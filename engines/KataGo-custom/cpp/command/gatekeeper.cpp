#include "../core/global.h"
#include "../core/datetime.h"
#include "../core/fileutils.h"
#include "../core/makedir.h"
#include "../core/config_parser.h"
#include "../core/timer.h"
#include "../core/threadsafequeue.h"
#include "../dataio/sgf.h"
#include "../dataio/trainingwrite.h"
#include "../dataio/loadmodel.h"
#include "../search/asyncbot.h"
#include "../program/setup.h"
#include "../program/play.h"
#include "../command/commandline.h"
#include "../main.h"

#include <sstream>

#include <cstdio>
#include <chrono>
#include <csignal>

using namespace std;

static std::atomic<bool> sigReceived(false);
static std::atomic<bool> shouldStop(false);
static void signalHandler(int signal)
{
  if(signal == SIGINT || signal == SIGTERM) {
    sigReceived.store(true);
    shouldStop.store(true);
  }
}

//-----------------------------------------------------------------------------------------


//Wraps together a neural net and handles for outputting training data for it.
//There should be one of these active for each gatekeeping match we run, and one active thread
//looping and actually performing the data output
//DOES take ownership of the NNEvaluators
namespace {
  struct NetAndStuff {
    string modelNameBaseline;
    string modelNameCandidate;
    NNEvaluator* nnEvalBaseline;
    NNEvaluator* nnEvalCandidate;
    const SearchParams searchParamsBaseline;
    const SearchParams searchParamsCandidate;
    MatchPairer* matchPairer;


    ThreadSafeQueue<FinishedGameData*> finishedGameQueue;
    int numGameThreads;
    bool isDraining;

    double drawEquivalentWinsForWhite;
    double noResultUtilityForWhite;

    int numGamesTallied;
    double numBaselineWinPoints;
    double numCandidateWinPoints;
    // If true, then break the game loop early if one model is going to achieve a majority of points.
    bool terminateEarlyOnPointMajority;

    ofstream* sgfOut;

    std::atomic<bool> terminated;

  public:
    NetAndStuff(ConfigParser& cfg, const string& nameB, const string& nameC, NNEvaluator* nevalB, NNEvaluator* nevalC, const SearchParams& searchParamsB, const SearchParams& searchParamsC, bool terminateEarlyOnPointMaj, ofstream* sOut)
      :modelNameBaseline(nameB),
       modelNameCandidate(nameC),
       nnEvalBaseline(nevalB),
       nnEvalCandidate(nevalC),
       searchParamsBaseline(searchParamsB),
       searchParamsCandidate(searchParamsC),
       matchPairer(NULL),
       finishedGameQueue(),
       numGameThreads(0),
       isDraining(false),
       drawEquivalentWinsForWhite(0.5),
       noResultUtilityForWhite(0.0),
       numGamesTallied(0),
       numBaselineWinPoints(0.0),
       numCandidateWinPoints(0.0),
       terminateEarlyOnPointMajority(terminateEarlyOnPointMaj),
       sgfOut(sOut),
       terminated(false)
    {
      assert(searchParamsBaseline.drawEquivalentWinsForWhite == searchParamsCandidate.drawEquivalentWinsForWhite);
      assert(searchParamsBaseline.noResultUtilityForWhite == searchParamsCandidate.noResultUtilityForWhite);
      drawEquivalentWinsForWhite = searchParamsBaseline.drawEquivalentWinsForWhite;
      noResultUtilityForWhite = searchParamsBaseline.noResultUtilityForWhite;

      //Initialize object for randomly pairing bots. Actually since this is only selfplay, this only
      //ever gives is the trivial base-vs-candidate pairing, but we use it also for keeping the game count and some logging.
      int64_t numGamesTotal = cfg.getInt64("numGamesPerGating",0,((int64_t)1) << 24);
      matchPairer = new MatchPairer(
        cfg,
        2,
        {modelNameBaseline,modelNameCandidate},
        {nnEvalBaseline,nnEvalCandidate},
        {searchParamsBaseline, searchParamsCandidate},
        {{0,1},{1,0}},
        numGamesTotal
      );
    }

    ~NetAndStuff() {
      delete matchPairer;
      delete nnEvalCandidate;
      delete nnEvalBaseline;
      if(sgfOut != NULL)
        delete sgfOut;
    }

    void runWriteDataLoop(Logger& logger) {
      while(true) {
        FinishedGameData* data;
        bool suc = finishedGameQueue.waitPop(data);
        if(!suc || data == NULL)
          break;

        double whitePoints;
        double blackPoints;
        if(data->endHist.isGameFinished && data->endHist.isNoResult) {
          whitePoints = drawEquivalentWinsForWhite;
          blackPoints = 1.0 - whitePoints;
          logger.write("Game " + Global::intToString(numGamesTallied) + ": noresult");
        }
        else {
          BoardHistory hist(data->endHist);
          Board endBoard = hist.getRecentBoard(0);
          //Force game end just in caseif we crossed a move limit
          if(!hist.isGameFinished)
            hist.endAndScoreGameNow(endBoard);

          ostringstream oresult;
          WriteSgf::printGameResult(oresult,hist);
          if(hist.winner == P_BLACK) {
            whitePoints = 0.0;
            blackPoints = 1.0;
            logger.write("Game " + Global::intToString(numGamesTallied) + ": winner black " + data->bName + " " + oresult.str());
          }
          else if(hist.winner == P_WHITE) {
            whitePoints = 1.0;
            blackPoints = 0.0;
            logger.write("Game " + Global::intToString(numGamesTallied) + ": winner white " + data->wName + " " + oresult.str());
          }
          else {
            whitePoints = 0.5 * noResultUtilityForWhite + 0.5;
            blackPoints = 1.0 - whitePoints;
            logger.write("Game " + Global::intToString(numGamesTallied) + ": draw " + oresult.str());
          }
        }

        numGamesTallied++;
        numBaselineWinPoints += (data->bIdx == 0) ? blackPoints : whitePoints;
        numCandidateWinPoints += (data->bIdx == 1) ? blackPoints : whitePoints;

        if(sgfOut != NULL) {
          assert(data->startHist.moveHistory.size() <= data->endHist.moveHistory.size());
          WriteSgf::writeSgf(*sgfOut,data->bName,data->wName,data->endHist,data,false,true);
          (*sgfOut) << endl;
        }
        delete data;

        //Terminate games if one side has won enough to guarantee the victory.
        int64_t numGamesRemaining = matchPairer->getNumGamesTotalToGenerate() - numGamesTallied;
        assert(numGamesRemaining >= 0);
        if(numGamesRemaining > 0 && terminateEarlyOnPointMajority) {
          if(numCandidateWinPoints >= (numBaselineWinPoints + numGamesRemaining)) {
            logger.write("Candidate has already won enough games, terminating remaning games");
            terminated.store(true);
          }
          else if(numBaselineWinPoints > numCandidateWinPoints + numGamesRemaining + 1e-10) {
            logger.write("Candidate has already lost too many games, terminating remaning games");
            terminated.store(true);
          }
        }

      }

      if(sgfOut != NULL)
        sgfOut->close();
    }

    //NOT threadsafe - needs to be externally synchronized
    //Game threads beginning a game using this net call this
    void registerGameThread() {
      assert(!isDraining);
      numGameThreads++;
    }

    //NOT threadsafe - needs to be externally synchronized
    //Game threads finishing a game using this net call this
    void unregisterGameThread() {
      numGameThreads--;
    }

    //NOT threadsafe - needs to be externally synchronized
    //Mark that we should start draining this net and not starting new games with it
    void markAsDraining() {
      if(!isDraining) {
        isDraining = true;
        finishedGameQueue.setReadOnly();
      }
    }
  };

  // (for victimplay) Data about evaluation results of an adversary vs a victim.
  struct AdversaryVsVictimInfo {
    string adversaryModelName;
    string victimModelName;
    string victimCfgContents;
    double adversaryPoints = 0.0;
    double victimPoints = 0.0;
    int numGamesTallied = 0;

    AdversaryVsVictimInfo(
      string adversaryModelName_ = "",
      string victimModelName_ = "",
      string victimCfgContents_ = "",
      double adversaryPoints_ = 0.0,
      double victimPoints_ = 0.0,
      int numGamesTallied_ = 0
    ) : adversaryModelName(std::move(adversaryModelName_))
      , victimModelName(std::move(victimModelName_))
      , victimCfgContents(std::move(victimCfgContents_))
      , adversaryPoints(adversaryPoints_)
      , victimPoints(victimPoints_)
      , numGamesTallied(numGamesTallied_) {}

    // Returns true if `other` describes the same adversary and victim as
    // `this`.
    bool isSameMatchup(const AdversaryVsVictimInfo& other) const {
      return getMatchup() == other.getMatchup();
    }

   private:
    tuple<string, string, string> getMatchup() const {
      return std::tie(adversaryModelName, victimModelName, victimCfgContents);
    }
  };

  // Info about model returned by getLatestModelInfo().
  struct ModelFileInfo {
    string name;
    string file;
    string dir;
    time_t time;
  };

  // Returns info about latest model in a directory.
  // (Wrapper for LoadModel::findLatestModel().)
  optional<ModelFileInfo> getLatestModelInfo(
      Logger& logger,
      const string& modelsDir,
      bool allowRandomNet
  ) {
    ModelFileInfo info;
    const bool foundModel = LoadModel::findLatestModel(modelsDir, logger, info.name, info.file, info.dir, info.time);
    if (!foundModel || (!allowRandomNet && info.file == "/dev/null")) {
      return {};
    }
    return info;
  }

  // Sleep for `seconds` seconds.
  void sleep(size_t seconds) {
    for (size_t i = 0; i < seconds; i++) {
      std::this_thread::sleep_for(std::chrono::seconds(1));
      if(shouldStop.load())
        break;
    }
  }
}

static void moveModel(const string& modelName, const string& modelFile, const string& modelDir, const string& testModelsDir, const string& intoDir, Logger& logger) {
  // Was the rejected model rooted in the testModels dir itself?
  if(FileUtils::weaklyCanonical(modelDir) == FileUtils::weaklyCanonical(testModelsDir)) {
    string renameDest = intoDir + "/" + modelName;
    logger.write("Moving " + modelFile + " to " + renameDest);
    FileUtils::rename(modelFile,renameDest);
  }
  // Or was it contained in a subdirectory
  else if(Global::isPrefix(FileUtils::weaklyCanonical(modelDir), FileUtils::weaklyCanonical(testModelsDir))) {
    string renameDest = intoDir + "/" + modelName;
    logger.write("Moving " + modelDir + " to " + renameDest);
    FileUtils::rename(modelDir,renameDest);
  }
  else {
    throw StringError("Model " + modelDir + " does not appear to be a subdir of " + testModelsDir + " can't figure out where how to move it to accept or reject it");
  }
}


//-----------------------------------------------------------------------------------------


int MainCmds::gatekeeper(const vector<string>& args, bool victimplay) {
  Board::initHash();
  ScoreValue::initTables();
  Rand seedRand;

  ConfigParser cfg;
  string testModelsDir;
  string acceptedModelsDir;
  string rejectedModelsDir;
  string victimModelsDir;
  string sgfOutputDir;
  string selfplayDir;
  bool noAutoRejectOldModels;
  bool quitIfNoNetsToTest;
  try {
    KataGoCommandLine cmd("Test neural nets to see if they should be accepted for self-play training data generation.");
    cmd.addConfigFileArg("","");
    cmd.addOverrideConfigArg();

    TCLAP::ValueArg<string> testModelsDirArg("","test-models-dir","Dir to poll and load models from",true,string(),"DIR");
    TCLAP::ValueArg<string> sgfOutputDirArg("","sgf-output-dir","Dir to output sgf files",true,string(),"DIR");
    TCLAP::ValueArg<string> acceptedModelsDirArg("","accepted-models-dir","Dir to write good models to",true,string(),"DIR");
    TCLAP::ValueArg<string> rejectedModelsDirArg("","rejected-models-dir","Dir to write bad models to",true,string(),"DIR");
    TCLAP::ValueArg<string> victimModelsDirArg("","victim-models-dir","Dir of victim models",true,string(),"DIR");
    TCLAP::ValueArg<string> selfplayDirArg("","selfplay-dir","Dir where selfplay data will be produced if a model passes",false,string(),"DIR");
    TCLAP::SwitchArg noAutoRejectOldModelsArg("","no-autoreject-old-models","Test older models than the latest accepted model");
    TCLAP::SwitchArg quitIfNoNetsToTestArg("","quit-if-no-nets-to-test","Terminate instead of waiting for a new net to test");
    cmd.add(testModelsDirArg);
    cmd.add(sgfOutputDirArg);
    cmd.add(acceptedModelsDirArg);
    cmd.add(rejectedModelsDirArg);
    if (victimplay) {
      cmd.add(victimModelsDirArg);
    }
    cmd.add(selfplayDirArg);
    cmd.setShortUsageArgLimit();
    cmd.add(noAutoRejectOldModelsArg);
    cmd.add(quitIfNoNetsToTestArg);
    cmd.parseArgs(args);

    testModelsDir = testModelsDirArg.getValue();
    sgfOutputDir = sgfOutputDirArg.getValue();
    acceptedModelsDir = acceptedModelsDirArg.getValue();
    rejectedModelsDir = rejectedModelsDirArg.getValue();
    victimModelsDir = victimModelsDirArg.getValue();
    selfplayDir = selfplayDirArg.getValue();
    noAutoRejectOldModels = noAutoRejectOldModelsArg.getValue();
    quitIfNoNetsToTest = quitIfNoNetsToTestArg.getValue();

    auto checkDirNonEmpty = [](const char* flag, const string& s) {
      if(s.length() <= 0)
        throw StringError("Empty directory specified for " + string(flag));
    };
    checkDirNonEmpty("test-models-dir",testModelsDir);
    checkDirNonEmpty("sgf-output-dir",sgfOutputDir);
    checkDirNonEmpty("accepted-models-dir",acceptedModelsDir);
    checkDirNonEmpty("rejected-models-dir",rejectedModelsDir);
    if (victimplay) {
      checkDirNonEmpty("victim-models-dir",victimModelsDir);
    }

    //Tolerate this argument being optional
    //checkDirNonEmpty("selfplay-dir",selfplayDir);

    cmd.getConfig(cfg);
  }
  catch (TCLAP::ArgException &e) {
    cerr << "Error: " << e.error() << " for argument " << e.argId() << endl;
    return 1;
  }

  MakeDir::make(testModelsDir);
  MakeDir::make(acceptedModelsDir);
  MakeDir::make(rejectedModelsDir);
  MakeDir::make(sgfOutputDir);
  if (victimModelsDir != "")
    MakeDir::make(victimModelsDir);
  if(selfplayDir != "")
    MakeDir::make(selfplayDir);

  Logger logger(&cfg);
  //Log to random file name to better support starting/stopping as well as multiple parallel runs
  logger.addFile(sgfOutputDir + "/log" + DateTime::getCompactDateTimeString() + "-" + Global::uint64ToHexString(seedRand.nextUInt64()) + ".log");

  logger.write("Gatekeeper Engine starting...");
  logger.write(string("Git revision: ") + Version::getGitRevision());

  //Load runner settings
  const int numGameThreads = cfg.getInt("numGameThreads",1,16384);
  const string gameSeedBase = Global::uint64ToHexString(seedRand.nextUInt64());

  PlaySettings playSettings = PlaySettings::loadForGatekeeper(cfg);
  GameRunner* gameRunner = new GameRunner(cfg, playSettings, logger);
  const int minBoardXSizeUsed = gameRunner->getGameInitializer()->getMinBoardXSize();
  const int minBoardYSizeUsed = gameRunner->getGameInitializer()->getMinBoardYSize();
  const int maxBoardXSizeUsed = gameRunner->getGameInitializer()->getMaxBoardXSize();
  const int maxBoardYSizeUsed = gameRunner->getGameInitializer()->getMaxBoardYSize();

  Setup::initializeSession(cfg);
  vector<SearchParams> paramss = Setup::loadParams(cfg, Setup::SETUP_FOR_OTHER);
  vector<SearchParams> originalParamss = paramss;
  if (victimplay) assert(1 <= paramss.size() && paramss.size() <= 2);
  else assert(paramss.size() == 1);

  //Done loading!
  //------------------------------------------------------------------------------------
  logger.write("Loaded all config stuff, watching for new neural nets in " + testModelsDir);
  if(!logger.isLoggingToStdout())
    cout << "Loaded all config stuff, watching for new neural nets in " + testModelsDir << endl;

  if(!std::atomic_is_lock_free(&shouldStop))
    throw StringError("shouldStop is not lock free, signal-quitting mechanism for terminating matches will NOT work!");
  std::signal(SIGINT, signalHandler);
  std::signal(SIGTERM, signalHandler);

  std::mutex netAndStuffMutex;
  NetAndStuff* netAndStuff = NULL;
  bool netAndStuffDataIsWritten = false;
  std::condition_variable waitNetAndStuffDataIsWritten;

  //Looping thread for writing data for a single net
  auto dataWriteLoop = [&netAndStuffMutex,&netAndStuff,&netAndStuffDataIsWritten,&waitNetAndStuffDataIsWritten,&logger]() {
    string modelNameBaseline = netAndStuff->modelNameBaseline;
    string modelNameCandidate = netAndStuff->modelNameCandidate;
    logger.write("Data write loop starting for neural net: " + modelNameBaseline + " vs " + modelNameCandidate);
    netAndStuff->runWriteDataLoop(logger);
    logger.write("Data write loop finishing for neural net: " + modelNameBaseline + " vs " + modelNameCandidate);

    std::unique_lock<std::mutex> lock(netAndStuffMutex);
    netAndStuffDataIsWritten = true;
    waitNetAndStuffDataIsWritten.notify_all();

    lock.unlock();
    logger.write("Data write loop cleaned up and terminating for " + modelNameBaseline + " vs " + modelNameCandidate);
  };
  auto dataWriteLoopProtected = [&logger,&dataWriteLoop]() {
    Logger::logThreadUncaught("data write loop", &logger, dataWriteLoop);
  };

  // Rejects old test models. Returns true if the test model was rejected.
  const auto rejectOldTestModel = [noAutoRejectOldModels,&testModelsDir,&rejectedModelsDir,&logger](
      const ModelFileInfo& testModelInfo,
      const ModelFileInfo& acceptedModelInfo
  ) -> bool {
    if (acceptedModelInfo.time <= testModelInfo.time || noAutoRejectOldModels) {
      return false;
    }
    logger.write("Rejecting " + testModelInfo.name + " automatically since older than best accepted model");
    moveModel(testModelInfo.name, testModelInfo.file, testModelInfo.dir, testModelsDir, rejectedModelsDir, logger);
    return true;
  };
  const auto loadNNEvaluator = [&logger,numGameThreads,minBoardXSizeUsed,maxBoardXSizeUsed,minBoardYSizeUsed,maxBoardYSizeUsed,&cfg](
      const string& modelName,
      const string& modelFile,
      int numSearchThreads
  ) -> NNEvaluator* {
    // * 2 + 16 just in case to have plenty of room
    const int maxConcurrentEvals = numSearchThreads * numGameThreads * 2 + 16;
    const int expectedConcurrentEvals = numSearchThreads * numGameThreads;
    const int defaultMaxBatchSize = -1;
    const bool defaultRequireExactNNLen = minBoardXSizeUsed == maxBoardXSizeUsed && minBoardYSizeUsed == maxBoardYSizeUsed;
    const bool disableFP16 = false;
    const string expectedSha256 = "";

    Rand rand;
    return Setup::initializeNNEvaluator(
      modelName,modelFile,expectedSha256,cfg,logger,rand,maxConcurrentEvals,expectedConcurrentEvals,
      maxBoardXSizeUsed,maxBoardYSizeUsed,defaultMaxBatchSize,defaultRequireExactNNLen,disableFP16,
      Setup::SETUP_FOR_OTHER
    );
  };
  // `terminateGamesEarlyOnPointMajority`: If true, then break the NetAndStuff's
  // evaluation early if one model is going to win a majority of the time.
  const auto loadNetAndStuff = [&paramss,&loadNNEvaluator,&sgfOutputDir,&logger,&cfg](
      const ModelFileInfo& baselineModelInfo,
      const ModelFileInfo& testModelInfo,
      bool terminateGamesEarlyOnPointMajority
  ) -> NetAndStuff* {
    const SearchParams& victimSearchParams = paramss[0];
    const SearchParams& advSearchParams = paramss[paramss.size() - 1];
    NNEvaluator* testNNEval = loadNNEvaluator(testModelInfo.name, testModelInfo.file, advSearchParams.numThreads);
    logger.write("Loaded candidate neural net " + testModelInfo.name + " from: " + testModelInfo.file);
    NNEvaluator* baselineNNEval = loadNNEvaluator(baselineModelInfo.name, baselineModelInfo.file, victimSearchParams.numThreads);
    logger.write("Loaded baseline neural net " + baselineModelInfo.name + " from: " + baselineModelInfo.file);

    Rand rand;
    string sgfOutputDirThisModel = sgfOutputDir + "/" + testModelInfo.name;
    MakeDir::make(sgfOutputDirThisModel);
    {
      ofstream out;
      FileUtils::open(out, sgfOutputDirThisModel + "/" + "gatekeeper-" + Global::uint64ToHexString(rand.nextUInt64()) + ".cfg");
      out << cfg.getContents();
      out.close();
    }

    ofstream* sgfOut = NULL;
    if(sgfOutputDirThisModel.length() > 0) {
      sgfOut = new ofstream();
      FileUtils::open(*sgfOut, sgfOutputDirThisModel + "/" + Global::uint64ToHexString(rand.nextUInt64()) + ".sgfs");
    }
    NetAndStuff* newNet = new NetAndStuff(cfg, baselineModelInfo.name, testModelInfo.name, baselineNNEval, testNNEval, victimSearchParams, advSearchParams, terminateGamesEarlyOnPointMajority, sgfOut);

    //Check for unused config keys
    cfg.warnUnusedKeys(cerr,&logger);

    return newNet;
  };

  auto gameLoop = [
    &gameRunner,
    &logger,
    &netAndStuffMutex,
    &netAndStuff,
    &gameSeedBase
  ](int threadIdx) {
    std::unique_lock<std::mutex> lock(netAndStuffMutex);
    netAndStuff->registerGameThread();
    logger.write("Game loop thread " + Global::intToString(threadIdx) + " starting game testing candidate: " + netAndStuff->modelNameCandidate);

    auto shouldStopFunc = [&netAndStuff]() {
      return shouldStop.load() || netAndStuff->terminated.load();
    };
    WaitableFlag* shouldPause = nullptr;

    Rand thisLoopSeedRand;
    while(true) {
      if(shouldStopFunc())
        break;

      lock.unlock();

      FinishedGameData* gameData = NULL;

      MatchPairer::BotSpec botSpecB;
      MatchPairer::BotSpec botSpecW;
      if(netAndStuff->matchPairer->getMatchup(botSpecB, botSpecW, logger)) {
        string seed = gameSeedBase + ":" + Global::uint64ToHexString(thisLoopSeedRand.nextUInt64());
        gameData = gameRunner->runGame(
          seed, botSpecB, botSpecW, NULL, NULL, logger,
          shouldStopFunc, shouldPause, nullptr, nullptr, nullptr
        );
      }

      bool shouldContinue = gameData != NULL;
      if(gameData != NULL)
        netAndStuff->finishedGameQueue.waitPush(gameData);

      lock.lock();

      if(!shouldContinue)
        break;
    }

    netAndStuff->unregisterGameThread();

    lock.unlock();
    logger.write("Game loop thread " + Global::intToString(threadIdx) + " terminating");
  };
  auto gameLoopProtected = [&logger,&gameLoop](int threadIdx) {
    Logger::logThreadUncaught("game loop", &logger, [&](){ gameLoop(threadIdx); });
  };
  // Runs netAndStuff games. May quit early, in which case `shouldStop` will be
  // true.
  const auto evaluateNetAndStuff = [
    &netAndStuff,
    &netAndStuffDataIsWritten,
    &dataWriteLoopProtected,
    &netAndStuffMutex,
    &waitNetAndStuffDataIsWritten,
    &logger,
    numGameThreads,
    &gameLoopProtected
  ]() {
    assert(netAndStuff != NULL);
    //Check again if we should be stopping, after loading the new net, and quit more quickly.
    if(shouldStop.load()) {
      return;
    }
    netAndStuffDataIsWritten = false;
    logger.write(
      Global::strprintf(
        "Evaluating %s vs. %s",
        netAndStuff->modelNameBaseline.c_str(),
        netAndStuff->modelNameCandidate.c_str()
      )
    );

    //And spawn off all the threads
    std::thread newThread(dataWriteLoopProtected);
    newThread.detach();
    vector<std::thread> threads;
    for(int i = 0; i<numGameThreads; i++) {
      threads.push_back(std::thread(gameLoopProtected,i));
    }

    //Wait for all game threads to stop
    for(int i = 0; i<threads.size(); i++)
      threads[i].join();

    //Wait for the data to all be written
    {
      std::unique_lock<std::mutex> lock(netAndStuffMutex);

      //Mark as draining so the data write thread will quit
      netAndStuff->markAsDraining();

      while(!netAndStuffDataIsWritten) {
        waitNetAndStuffDataIsWritten.wait(lock);
      }
    }
  };

  // Victimplay-only variables
  AdversaryVsVictimInfo lastAcceptedModelResults;
  string victimCfgReloadPath = victimModelsDir + "/victim.cfg";

  //Looping polling for new neural nets and loading them in
  while(true) {
    if(shouldStop.load())
      break;

    assert(netAndStuff == NULL);
    const optional<ModelFileInfo> acceptedModelInfo = getLatestModelInfo(
        logger,
        acceptedModelsDir,
        true /*allowRandomNet*/
    );
    if (!acceptedModelInfo.has_value()) {
      logger.write("No accepted model found in " + acceptedModelsDir);
      sleep(4);
      continue;
    }

    optional<ModelFileInfo> testModelInfo = getLatestModelInfo(
        logger,
        testModelsDir,
        false /*allowRandomNet*/
    );
    if (testModelInfo.has_value()) {
      logger.write("Found new candidate neural net " + testModelInfo->name);
      if (rejectOldTestModel(*testModelInfo, *acceptedModelInfo)) {
        testModelInfo.reset();
      }
    } else if (quitIfNoNetsToTest) {
      break;
    }

    bool shouldAcceptTestModel = false;
    if (victimplay) {
      optional<ModelFileInfo> victimModelInfo = getLatestModelInfo(
          logger,
          victimModelsDir,
          false /*allowRandomNet*/
      );
      if (!victimModelInfo.has_value()) {
        logger.write("No victim model found in " + victimModelsDir);
        sleep(4);
        continue;
      }
      victimModelInfo->name = "victim-" + victimModelInfo->name;
      string victimCfgContents;
      ConfigParser victimCfg;
      if(FileUtils::exists(victimCfgReloadPath)) {
        try {
          victimCfg.initialize(victimCfgReloadPath);
          victimCfgContents = victimCfg.getAllKeyVals();
        } catch (const IOError &e) {
          logger.write(string("Victim config reloading error: ") + e.what());
        }
      }

      AdversaryVsVictimInfo acceptedModelMatchup{
        acceptedModelInfo->name,
        victimModelInfo->name,
        victimCfgContents,
      };
      if (!acceptedModelMatchup.isSameMatchup(lastAcceptedModelResults)) {
        // We need to re-evaluate accepted model vs. victim model.

        if (victimCfgContents != lastAcceptedModelResults.victimCfgContents) {
          // Update `paramss` with the new victim config.
          logger.write("Old victim config:\n" + lastAcceptedModelResults.victimCfgContents);
          logger.write("Reloading with config:\n" + victimCfgContents);
          paramss = originalParamss;
          Setup::loadParams(
              victimCfg,
              Setup::SETUP_FOR_OTHER,
              paramss,
              false /*applyDefaultParams*/
          );
          victimCfg.warnUnusedKeys(cerr, &logger);
        }

        netAndStuff = loadNetAndStuff(*victimModelInfo, *acceptedModelInfo, !victimplay);
        logger.write("Evaluating accepted model");
        evaluateNetAndStuff();
        if (shouldStop.load()) {
          break;
        }

        lastAcceptedModelResults = std::move(acceptedModelMatchup);
        lastAcceptedModelResults.adversaryPoints = netAndStuff->numCandidateWinPoints;
        lastAcceptedModelResults.victimPoints = netAndStuff->numBaselineWinPoints;
        lastAcceptedModelResults.numGamesTallied = netAndStuff->numGamesTallied;
        logger.write(
          Global::strprintf(
            "Accepted model %s scored %.3f to %.3f in %d games.",
            lastAcceptedModelResults.adversaryModelName.c_str(),
            lastAcceptedModelResults.adversaryPoints,
            lastAcceptedModelResults.victimPoints,
            lastAcceptedModelResults.numGamesTallied
          )
        );
        delete netAndStuff;
        netAndStuff = NULL;
      }

      if (!testModelInfo.has_value()) {
        sleep(4);
        continue;
      }
      // Evaluate new test model vs. victim.
      // We don't need to check for victimCfg updates here; if victimCfg
      // changed, then it should've been reloaded when re-evaluating the
      // accepted model.
      netAndStuff = loadNetAndStuff(*victimModelInfo, *testModelInfo, !victimplay);
      logger.write("Evaluating test model");
      evaluateNetAndStuff();
      if (shouldStop.load()) {
        break;
      }

      logger.write(
        Global::strprintf(
          "Test model %s scored %.3f to %.3f in %d games. (vs. accepted model %s scored %.3f to %.3f in %d games)",
          testModelInfo->name.c_str(),
          netAndStuff->numCandidateWinPoints,
          netAndStuff->numBaselineWinPoints,
          netAndStuff->numGamesTallied,
          lastAcceptedModelResults.adversaryModelName.c_str(),
          lastAcceptedModelResults.adversaryPoints,
          lastAcceptedModelResults.victimPoints,
          lastAcceptedModelResults.numGamesTallied
        )
      );
      assert(netAndStuff->numGamesTallied == lastAcceptedModelResults.numGamesTallied);
      // Test model wins ties.
      if(netAndStuff->numCandidateWinPoints + 1e-10 >= lastAcceptedModelResults.adversaryPoints) {
        shouldAcceptTestModel = true;
        lastAcceptedModelResults = AdversaryVsVictimInfo{
          testModelInfo->name,
          victimModelInfo->name,
          victimCfgContents,
          netAndStuff->numCandidateWinPoints,
          netAndStuff->numBaselineWinPoints,
          netAndStuff->numGamesTallied,
        };
      }
      delete netAndStuff;
      netAndStuff = NULL;
    } else {
      if (!testModelInfo.has_value()) {
        sleep(4);
        continue;
      }
      netAndStuff = loadNetAndStuff(*acceptedModelInfo, *testModelInfo, !victimplay);
      evaluateNetAndStuff();
      if (shouldStop.load()) {
        break;
      }
      logger.write(
        Global::strprintf(
          "Candidate %s scored %.3f to %.3f in %d games",
          netAndStuff->modelNameCandidate.c_str(),
          netAndStuff->numCandidateWinPoints,
          netAndStuff->numBaselineWinPoints,
          netAndStuff->numGamesTallied
        )
      );
      // Test model wins ties.
      shouldAcceptTestModel = netAndStuff->numCandidateWinPoints + 1e-10 >= netAndStuff->numBaselineWinPoints;
      delete netAndStuff;
      netAndStuff = NULL;
    }

    if (shouldAcceptTestModel) {
      assert(testModelInfo.has_value());
      //Make a bunch of the directories that selfplay will need so that there isn't a race on the selfplay
      //machines to concurrently make it, since sometimes concurrent making of the same directory can corrupt
      //a filesystem
      if(selfplayDir != "") {
        MakeDir::make(selfplayDir + "/" + testModelInfo->name);
        sleep(1);
        MakeDir::make(selfplayDir + "/" + testModelInfo->name + "/" + "sgfs");
        MakeDir::make(selfplayDir + "/" + testModelInfo->name + "/" + "tdata");
        MakeDir::make(selfplayDir + "/" + testModelInfo->name + "/" + "vadata");
      }
      sleep(2);

      logger.write("Accepting model " + testModelInfo->name);
      moveModel(testModelInfo->name, testModelInfo->file, testModelInfo->dir, testModelsDir, acceptedModelsDir, logger);
    } else if (testModelInfo.has_value()) {
      logger.write("Rejecting model " + testModelInfo->name);
      moveModel(testModelInfo->name, testModelInfo->file, testModelInfo->dir, testModelsDir, rejectedModelsDir, logger);
    }
  }
  delete netAndStuff;
  netAndStuff = NULL;

  //Delete and clean up everything else
  NeuralNet::globalCleanup();
  delete gameRunner;
  ScoreValue::freeTables();

  if(sigReceived.load())
    logger.write("Exited cleanly after signal");
  logger.write("All cleaned up, quitting");
  return 0;
}
