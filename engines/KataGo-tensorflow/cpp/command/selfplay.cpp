#include "../core/global.h"
#include "../core/datetime.h"
#include "../core/fileutils.h"
#include "../core/makedir.h"
#include "../core/config_parser.h"
#include "../dataio/sgf.h"
#include "../dataio/trainingwrite.h"
#include "../dataio/loadmodel.h"
#include "../neuralnet/modelversion.h"
#include "../search/asyncbot.h"
#include "../program/setup.h"
#include "../program/play.h"
#include "../program/selfplaymanager.h"
#include "../command/commandline.h"
#include "../main.h"

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

/**
 * Does not do any forking
 * Does not switch networks mid game.
 */
static FinishedGameData* runOneVictimplayGame(
  NNEvaluator* victimNNEval,
  NNEvaluator* advNNEval,
  const SearchParams &victimSearchParams,
  const SearchParams &advSearchParams,
  const Color advColor,
  GameRunner* gameRunner,
  const std::function<bool()>& shouldStopFunc,
  Logger &logger,
  const int gameIdx,
  const string &seed,
  NNEvaluator* predictorNNEval = nullptr
) {
  MatchPairer::BotSpec victimBotSpec;
  victimBotSpec.botIdx = 0; // victim is always idx 0
  victimBotSpec.botName = victimNNEval->getModelName();
  victimBotSpec.nnEval = victimNNEval;
  victimBotSpec.baseParams = victimSearchParams;

  MatchPairer::BotSpec adversaryBotSpec;
  adversaryBotSpec.botIdx = 1; // adversary is always idx 1
  adversaryBotSpec.botName = advNNEval->getModelName();
  adversaryBotSpec.nnEval = advNNEval;
  adversaryBotSpec.predictorNNEval = predictorNNEval;
  adversaryBotSpec.baseParams = advSearchParams;

  MatchPairer::BotSpec& botSpecB = advColor == C_BLACK ? adversaryBotSpec : victimBotSpec;
  MatchPairer::BotSpec& botSpecW = advColor == C_BLACK ? victimBotSpec : adversaryBotSpec;

  FinishedGameData* gameData = gameRunner->runGame(
    seed, botSpecB, botSpecW,
    nullptr, // forkData
    nullptr, // startPosSample
    logger,
    shouldStopFunc,
    nullptr, // shouldPause
    nullptr, // checkForNewNNEval
    nullptr, // afterInitialization
    nullptr  // onEachMove
  );

  const bool victimIsBlack = advColor == C_WHITE;
  const string victimColorStr = victimIsBlack ? "B" : "W";
  const string adversaryColorStr = victimIsBlack ? "W" : "B";
  const float victimMinusAdvScore =
    (victimIsBlack ? -1 : 1)
    * gameData->finalWhiteMinusBlackScore();

  logger.write(
    "Game #" + Global::int64ToString(gameIdx) +
    " victim (" + victimColorStr + ")" +
    " - adv (" + adversaryColorStr + ")" +
    " score: " + Global::floatToString(victimMinusAdvScore) +
    "; victim_" + victimSearchParams.getSearchAlgoAsStr() +
            "@" + Global::intToString(victimSearchParams.maxVisits) +
    " adv_" + advSearchParams.getSearchAlgoAsStr() +
        "@" + Global::intToString(advSearchParams.maxVisits)
  );

  return gameData;
}

int MainCmds::selfplay(const vector<string>& args, const bool victimplay) {
  Board::initHash();
  ScoreValue::initTables();
  Rand seedRand;

  ConfigParser cfg;
  string modelsDir;
  string outputDir;
  string victimOutputDir;
  string nnPredictorPath;
  string nnVictimPath;
  int64_t maxGamesTotal = ((int64_t)1) << 62;
  try {
    KataGoCommandLine cmd("Generate training data via self play.");
    cmd.addConfigFileArg("","");

    TCLAP::ValueArg<string> modelsDirArg("","models-dir","Dir to poll and load models from",true,string(),"DIR");
    TCLAP::ValueArg<string> outputDirArg("","output-dir","Dir to output files",true,string(),"DIR");
    TCLAP::ValueArg<string> maxGamesTotalArg("","max-games-total","Terminate after this many games",false,string(),"NGAMES");
    TCLAP::ValueArg<string> nnPredictorPathArg("","nn-predictor-path","Path to predictor model(s)",false,string(),"PREDICTOR");
    TCLAP::ValueArg<string> nnVictimPathArg("","nn-victim-path","Path to victim model(s)",victimplay,string(),"VICTIM");
    TCLAP::ValueArg<string> victimOutputDirArg("","victim-output-dir","Dir to output files for victim predictor training",false,string(),"DIR");
    cmd.add(modelsDirArg);
    cmd.add(outputDirArg);
    cmd.add(maxGamesTotalArg);
    cmd.add(nnPredictorPathArg);
    cmd.add(nnVictimPathArg);
    cmd.add(victimOutputDirArg);
    cmd.parseArgs(args);

    modelsDir = modelsDirArg.getValue();
    outputDir = outputDirArg.getValue();
    string maxGamesTotalStr = maxGamesTotalArg.getValue();
    if(maxGamesTotalStr != "") {
      bool suc = Global::tryStringToInt64(maxGamesTotalStr,maxGamesTotal);
      if(!suc || maxGamesTotal <= 0)
        throw StringError("-max-games-total must be a positive integer");
    }

    auto checkDirNonEmpty = [](const char* flag, const string& s) {
      if(s.length() <= 0)
        throw StringError("Empty directory specified for " + string(flag));
    };
    checkDirNonEmpty("models-dir",modelsDir);
    checkDirNonEmpty("output-dir",outputDir);

    nnPredictorPath = nnPredictorPathArg.getValue();
    nnVictimPath = nnVictimPathArg.getValue();
    victimOutputDir = victimOutputDirArg.getValue();

    cmd.getConfig(cfg);
  }
  catch (TCLAP::ArgException &e) {
    cerr << "Error: " << e.error() << " for argument " << e.argId() << endl;
    return 1;
  }

  MakeDir::make(outputDir);
  MakeDir::make(modelsDir);

  Logger logger(&cfg);
  //Log to random file name to better support starting/stopping as well as multiple parallel runs
  logger.addFile(outputDir + "/log" + DateTime::getCompactDateTimeString() + "-" + Global::uint64ToHexString(seedRand.nextUInt64()) + ".log");

  logger.write(string(victimplay ? "Victim" : "Self") + " Play Engine starting...");
  logger.write(string("Git revision: ") + Version::getGitRevision());

  //Load runner settings
  const int numGameThreads = cfg.getInt("numGameThreads",1,16384);
  const string gameSeedBase = Global::uint64ToHexString(seedRand.nextUInt64());

  //Width and height of the board to use when writing data, typically 19
  const int dataBoardLen = cfg.getInt("dataBoardLen",3,37);
  const int inputsVersion =
    cfg.contains("inputsVersion") ?
    cfg.getInt("inputsVersion",0,10000) :
    NNModelVersion::getInputsVersion(NNModelVersion::defaultModelVersion);
  //Max number of games that we will allow to be queued up and not written out
  const int maxDataQueueSize = cfg.getInt("maxDataQueueSize",1,1000000);
  const int maxRowsPerTrainFile = cfg.getInt("maxRowsPerTrainFile",1,100000000);
  const int maxRowsPerValFile = cfg.getInt("maxRowsPerValFile",1,100000000);
  const double firstFileRandMinProp = cfg.getDouble("firstFileRandMinProp",0.0,1.0);

  const double validationProp = cfg.getDouble("validationProp",0.0,0.5);
  const int64_t logGamesEvery = cfg.getInt64("logGamesEvery",1,1000000);

  const bool switchNetsMidGame = cfg.getBool("switchNetsMidGame");
  assert(!(victimplay && switchNetsMidGame));

  // Proportion of selfplay games to include during victimplay training.
  const double selfplayProportion =
    cfg.contains("selfplayProportion") ?
    cfg.getDouble("selfplayProportion", 0.0, 1.0) :
    0.0;
  assert(victimplay || selfplayProportion == 0.0);

  vector<SearchParams> paramss = Setup::loadParams(cfg, Setup::SETUP_FOR_OTHER);
  const vector<SearchParams> originalParamss = paramss;
  if (victimplay) assert(1 <= paramss.size() && paramss.size() <= 2);
  else assert(paramss.size() == 1);
  SearchParams baseParams = paramss[0];
  std::string lastVictimCfgContents = "";
  // Multithreaded use of paramss and lastVictimCfgContents should be guarded
  // with paramsReloadMutex to avoid races.
  mutex paramsReloadMutex;

  //Initialize object for randomizing game settings and running games
  PlaySettings playSettings = PlaySettings::loadForSelfplay(cfg);
  GameRunner* gameRunner = new GameRunner(cfg, playSettings, logger);
  bool autoCleanupAllButLatestIfUnused = true;
  SelfplayManager* manager = new SelfplayManager(validationProp, maxDataQueueSize, &logger, logGamesEvery, autoCleanupAllButLatestIfUnused);

  const int minBoardXSizeUsed = gameRunner->getGameInitializer()->getMinBoardXSize();
  const int minBoardYSizeUsed = gameRunner->getGameInitializer()->getMinBoardYSize();
  const int maxBoardXSizeUsed = gameRunner->getGameInitializer()->getMaxBoardXSize();
  const int maxBoardYSizeUsed = gameRunner->getGameInitializer()->getMaxBoardYSize();

  Setup::initializeSession(cfg);

  //Done loading!
  //------------------------------------------------------------------------------------
  logger.write("Loaded all config stuff, starting play");
  if(!logger.isLoggingToStdout())
    cout << "Loaded all config stuff, starting play" << endl;

  if(!std::atomic_is_lock_free(&shouldStop))
    throw StringError("shouldStop is not lock free, signal-quitting mechanism for terminating matches will NOT work!");
  std::signal(SIGINT, signalHandler);
  std::signal(SIGTERM, signalHandler);

  auto loadNN = [
    &cfg,
    &numGameThreads,
    &minBoardXSizeUsed,
    &maxBoardXSizeUsed,
    &minBoardYSizeUsed,
    &maxBoardYSizeUsed,
    &logger
  ](
    const string modelName,
    const string modelFile
  ) -> NNEvaluator* {
    const string expectedSha256 = "";
    Rand rand;
    const int maxConcurrentEvals = cfg.getInt("numSearchThreads") * numGameThreads * 2 + 16;
    const int expectedConcurrentEvals = cfg.getInt("numSearchThreads") * numGameThreads;
    const int defaultMaxBatchSize = -1;
    const bool defaultRequireExactNNLen = minBoardXSizeUsed == maxBoardXSizeUsed && minBoardYSizeUsed == maxBoardYSizeUsed;

    NNEvaluator* nnEval = Setup::initializeNNEvaluator(
      modelName,modelFile,expectedSha256,cfg,logger,rand,maxConcurrentEvals,expectedConcurrentEvals,
      maxBoardXSizeUsed,maxBoardYSizeUsed,defaultMaxBatchSize,defaultRequireExactNNLen,
      Setup::SETUP_FOR_OTHER
    );

    logger.write("Loaded " + modelName + " neural net from: " + modelFile);
    return nnEval;
  };

  // keep weak references to the victims loaded by game threads
  // for being able to find the model by name if at least one thread is using it
  // and allowing to automatically destroy the model when nobody uses it
  vector<weak_ptr<NNEvaluator>> victimNNEvals;
  mutex victimMutex;

  // keep model ownership if we have only one victim for all games
  shared_ptr<NNEvaluator> singleVictim;
  bool reloadVictims = false;

  if(victimplay) {
    // If victim path doesn't exist yet and isn't a gzip file, assume it's a
    // directory that has not yet been created yet.
    const bool isDirectory =
      (!FileUtils::exists(nnVictimPath) && !Global::isSuffix(nnVictimPath, ".gz"))
      || FileUtils::isDirectory(nnVictimPath);
    if(isDirectory) {
      // We load victims from a directory.
      // A new victim is loaded every time a new victim shows up in the directory.
      reloadVictims = true;
    } else {
      // A victim is loaded a single time from a file.
      singleVictim.reset(loadNN("victim", nnVictimPath));
      victimNNEvals.push_back(singleVictim);
    }
  }

  // Ditto for predictor models
  vector<weak_ptr<NNEvaluator>> predictorNNEvals;
  mutex predictorMutex;

  //Returns true if a new net was loaded.
  auto loadLatestNeuralNetIntoManager =
    [inputsVersion,&manager,maxRowsPerTrainFile,maxRowsPerValFile,firstFileRandMinProp,dataBoardLen,selfplayProportion,
     &loadNN,
     &modelsDir,&outputDir,&victimOutputDir,&logger,&cfg,numGameThreads,victimplay,
     minBoardXSizeUsed,maxBoardXSizeUsed,minBoardYSizeUsed,maxBoardYSizeUsed](const string* lastNetName) -> bool {

    string modelName;
    string modelFile;
    string modelDir;
    time_t modelTime;
    bool foundModel = LoadModel::findLatestModel(modelsDir, logger, modelName, modelFile, modelDir, modelTime);

    //No new neural nets yet
    if(!foundModel || (lastNetName != NULL && *lastNetName == modelName))
      return false;
    if(modelName == "random" && lastNetName != NULL && *lastNetName != "random") {
      logger.write("WARNING: " + *lastNetName + " was the previous model, but now no model was found. Continuing with prev model instead of using random");
      return false;
    }

    logger.write("Found new neural net " + modelName);

    NNEvaluator* nnEval = loadNN(modelName, modelFile);

    string modelOutputDir = outputDir + "/" + modelName;
    string sgfOutputDir = modelOutputDir + "/sgfs";
    string tdataOutputDir = modelOutputDir + "/tdata";
    string vdataOutputDir = modelOutputDir + "/vdata";

    string tdataVictimOutputDir, vdataVictimOutputDir;
    if(victimOutputDir != "") {
      tdataVictimOutputDir = victimOutputDir + "/tdata";
      vdataVictimOutputDir = victimOutputDir + "/vdata";
    }

    //Try repeatedly to make directories, in case the filesystem is unhappy with us as we try to make the same dirs as another process.
    //Wait a random amount of time in between each failure.
    Rand rand;
    int maxTries = 5;
    for(int i = 0; i<maxTries; i++) {
      bool success = false;
      try {
        MakeDir::make(modelOutputDir);
        MakeDir::make(sgfOutputDir);
        MakeDir::make(tdataOutputDir);
        MakeDir::make(vdataOutputDir);

        if (victimOutputDir != "") {
          MakeDir::make(victimOutputDir);
          MakeDir::make(tdataVictimOutputDir);
          MakeDir::make(vdataVictimOutputDir);
        }
        success = true;
      }
      catch(const StringError& e) {
        logger.write(string("WARNING, error making directories, trying again shortly: ") + e.what());
        success = false;
      }

      if(success)
        break;
      else {
        if(i == maxTries-1) {
          logger.write("ERROR: Could not make selfplay model directories, is something wrong with the filesystem?");
          //Just give up and wait for the next model.
          return false;
        }
        double sleepTime = 10.0 + rand.nextDouble() * 30.0;
        std::this_thread::sleep_for(std::chrono::duration<double>(sleepTime));
        continue;
      }
    }

    {
      ofstream out;
      FileUtils::open(out,modelOutputDir + "/" + "selfplay-" + Global::uint64ToHexString(rand.nextUInt64()) + ".cfg");
      out << cfg.getContents();
      out.close();
    }

    //Note that this inputsVersion passed here is NOT necessarily the same as the one used in the neural net self play, it
    //simply controls the input feature version for the written data
    int onlyWriteEvery = 1;
    TrainingDataWriter* tdataWriter = new TrainingDataWriter(
      tdataOutputDir, tdataVictimOutputDir, NULL, inputsVersion, maxRowsPerTrainFile,
      firstFileRandMinProp, dataBoardLen, dataBoardLen, onlyWriteEvery, Global::uint64ToHexString(rand.nextUInt64())
    );
    TrainingDataWriter* vdataWriter = new TrainingDataWriter(
      vdataOutputDir, vdataVictimOutputDir, NULL, inputsVersion, maxRowsPerValFile,
      firstFileRandMinProp, dataBoardLen, dataBoardLen, onlyWriteEvery, Global::uint64ToHexString(rand.nextUInt64())
    );

    tdataWriter->forVictimplay = victimplay;
    vdataWriter->forVictimplay = victimplay;
    tdataWriter->allowSelfplayInVictimplay = selfplayProportion > 0.0;
    vdataWriter->allowSelfplayInVictimplay = selfplayProportion > 0.0;

    tdataWriter->useAuxPolicyTarget = cfg.getBool("useAuxPolicyTarget");
    vdataWriter->useAuxPolicyTarget = cfg.getBool("useAuxPolicyTarget");

    ofstream* sgfOut = NULL;
    if(sgfOutputDir.length() > 0) {
      sgfOut = new ofstream();
      FileUtils::open(*sgfOut, sgfOutputDir + "/" + Global::uint64ToHexString(rand.nextUInt64()) + ".sgfs");
    }

    logger.write("Model loading loop thread loaded new neural net " + nnEval->getModelName());
    manager->loadModelAndStartDataWriting(nnEval, tdataWriter, vdataWriter, sgfOut);
    return true;
  };

  //Initialize the initial neural net
  {
    bool success = loadLatestNeuralNetIntoManager(NULL);
    if(!success)
      throw StringError("Either could not load latest neural net or access/write appopriate directories");
  }

  //Check for unused config keys
  cfg.warnUnusedKeys(cerr,&logger);

  //Shared logic for (re)loading victim and predictor models
  auto modelLoad = [&loadNN](
    string modelPath,
    string humanModelName,
    vector<weak_ptr<NNEvaluator>>& existingNNEvals,
    Logger& loadLogger,
    string logPrefix,
    mutex& modelMutex,
    bool allowRandom
  ) -> std::shared_ptr<NNEvaluator> {
    shared_ptr<NNEvaluator> outputPtr;
    string modelName = "random";
    string modelFile;
    string modelDir;
    time_t modelTime;

    // Keep trying to load the model until we succeed
    while (!FileUtils::exists(modelPath)) {
      loadLogger.write(humanModelName + " model path " + modelPath + " does not exist yet, waiting 30 sec...");
      std::this_thread::sleep_for(std::chrono::seconds(30));
    }
    while (
      !LoadModel::findLatestModel(modelPath, loadLogger, modelName, modelFile, modelDir, modelTime) ||
      (!allowRandom && modelName == "random")
    ) {
      loadLogger.write("No " + humanModelName + " available yet, waiting 30 sec...");
      std::this_thread::sleep_for(std::chrono::seconds(30));
    }

    modelName = humanModelName + "-" + modelName;
    bool modelLoaded = false;
    int modelsReleased = 0;
    std::vector<int> evalsInUse;
    // scope for the mutex
    {
      lock_guard<mutex> lock(modelMutex);

      // do not increase loop iterator by default
      // since we'd like to sanitize the container in-place
      for(auto it = existingNNEvals.begin(); it != existingNNEvals.end(); ) {
        // 'it' is a weak_ptr<NNEvaluator>
        shared_ptr<NNEvaluator> eval = it->lock();
        if (!eval) {
          // all references released, we can safely remove it
          it = existingNNEvals.erase(it);
          ++modelsReleased;
          continue;
        }

        evalsInUse.push_back(eval.use_count() - 1);

        if (eval->getModelName() == modelName) {
          // found it already loaded, transfer ownership
          swap(eval, outputPtr);
          break;
        }
        ++it;
      }

      // nothing was found, load the new model
      if(!outputPtr) {
        modelLoaded = true;
        outputPtr.reset(loadNN(modelName, modelFile));
        existingNNEvals.push_back(outputPtr);
      }
    }

    // we must have the evaluator here (either found or loaded)
    // since the model definitely exists
    assert(outputPtr);

    std::string log_str;
    if(modelLoaded) {
      log_str += "\n  loaded " + humanModelName + ":" + modelName;
    }
    if(modelsReleased > 0) {
      log_str += "\n sanitized " + to_string(modelsReleased) + " " + humanModelName + "s";
    }
    if(evalsInUse.size() > 1) {
      log_str += "\n " + humanModelName + " counters in use:";
      for(const auto& c: evalsInUse)
        log_str += " " + to_string(c);
    }
    if(!log_str.empty()) {
      loadLogger.write(logPrefix + log_str);
    }
    return outputPtr;
  };

  //Shared across all game loop threads
  std::atomic<int64_t> numGamesStarted(0);
  ForkData* forkData = new ForkData();
  auto gameLoop = [
    &gameRunner,
    &manager,
    &logger,
    switchNetsMidGame,
    selfplayProportion,
    &numGamesStarted,
    &forkData,
    maxGamesTotal,
    &paramss,
    &originalParamss,
    &baseParams,
    &paramsReloadMutex,
    &lastVictimCfgContents,
    &gameSeedBase,
    &victimplay,
    &reloadVictims,
    &victimNNEvals,
    &victimMutex,
    &nnVictimPath,
    &nnPredictorPath,
    &predictorNNEvals,
    &predictorMutex,
    &modelLoad
  ](int threadIdx) {
    auto shouldStopFunc = []() noexcept {
      return shouldStop.load();
    };
    WaitableFlag* shouldPause = nullptr;

    string prevModelName;
    Rand thisLoopSeedRand;
    std::string victimCfgReloadPath = nnVictimPath + "/victim.cfg";
    std::string logPrefix = "Game loop thread " + to_string(threadIdx) + ": ";
    while(true) {
      if(shouldStop.load())
        break;

      shared_ptr<NNEvaluator> curVictimNNEval;
      SearchParams curVictimSearchParams;
      SearchParams curAdvSearchParams;
      if(reloadVictims) {
        curVictimNNEval = modelLoad(
          nnVictimPath,
          "victim",
          victimNNEvals,
          logger,
          logPrefix,
          victimMutex,
          false
        );

        if(FileUtils::exists(victimCfgReloadPath)) {
          ConfigParser victimCfg;
          try {
            victimCfg.initialize(victimCfgReloadPath);
            {
              lock_guard<mutex> lock(paramsReloadMutex);
              std::string victimCfgContents = victimCfg.getAllKeyVals();
              if (victimCfgContents != lastVictimCfgContents) {
                logger.write("Old victim config:\n" + lastVictimCfgContents);
                logger.write("Reloading with config:\n" + victimCfgContents);
                paramss = originalParamss;
                Setup::loadParams(
                    victimCfg,
                    Setup::SETUP_FOR_OTHER,
                    paramss,
                    false /*applyDefaultParams*/
                );
                victimCfg.warnUnusedKeys(cerr, &logger);
                lastVictimCfgContents = std::move(victimCfgContents);
              }
            }  // end of mutex scope
          } catch (const IOError &e) {
            logger.write(logPrefix + "victim config reloading error: " + e.what());
          }
        }
      } else if (victimplay) {
        // no need for the mutex here since we never modify victimNNEval
        assert(victimNNEvals.size() == 1);
        curVictimNNEval = victimNNEvals[0].lock();
      }

      shared_ptr<NNEvaluator> curPredictorNNEval;
      if (nnPredictorPath != "") {
        curPredictorNNEval = modelLoad(
          nnPredictorPath,
          "predictor",
          predictorNNEvals,
          logger,
          logPrefix,
          predictorMutex,
          true
        );
      }

      // get the latest search parameters copy
      // (probably changed from another thread at this point)
      {
        lock_guard<mutex> lock(paramsReloadMutex);
        curVictimSearchParams = paramss[0];
        curAdvSearchParams = paramss[paramss.size() - 1];
      }

      NNEvaluator* nnEval = manager->acquireLatest();
      assert(nnEval != NULL);

      if(prevModelName != nnEval->getModelName()) {
        prevModelName = nnEval->getModelName();
        logger.write(logPrefix + "starting game on new neural net: " + prevModelName);
      }

      //Callback that runGame will call periodically to ask us if we have a new neural net
      std::function<NNEvaluator*()> checkForNewNNEval = [&manager,&nnEval,&prevModelName,&logger,&logPrefix]() -> NNEvaluator* {
        NNEvaluator* newNNEval = manager->acquireLatest();
        assert(newNNEval != NULL);
        if(newNNEval == nnEval) {
          manager->release(newNNEval);
          return NULL;
        }
        manager->release(nnEval);

        nnEval = newNNEval;
        prevModelName = nnEval->getModelName();
        logger.write(logPrefix + "changing midgame to new neural net: " + prevModelName);
        return nnEval;
      };

      FinishedGameData* gameData = NULL;

      int64_t gameIdx = numGamesStarted.fetch_add(1,std::memory_order_acq_rel);
      if (gameIdx >= maxGamesTotal) {
        // Do nothing.
      } else if(victimplay) {
        manager->countOneGameStarted(nnEval);
        const string seed = gameSeedBase + ":" + Global::uint64ToHexString(thisLoopSeedRand.nextUInt64());
        if (thisLoopSeedRand.nextDouble() >= selfplayProportion) {  // victimplay game
          gameData = runOneVictimplayGame(
            curVictimNNEval.get(), nnEval,
            curVictimSearchParams, curAdvSearchParams,
            gameIdx % 2 == 0 ? C_BLACK : C_WHITE,
            gameRunner, shouldStopFunc, logger,
            gameIdx, seed, curPredictorNNEval.get()
          );
        } else {  // selfplay game
          MatchPairer::BotSpec botSpecB;
          botSpecB.botIdx = 1;
          botSpecB.botName = nnEval->getModelName();
          botSpecB.nnEval = nnEval;
          botSpecB.baseParams = curAdvSearchParams;
          // A-MCTS is not helpful during selfplay, so let's make selfplay games run MCTS.
          botSpecB.baseParams.searchAlgo = SearchParams::SearchAlgorithm::MCTS;
          MatchPairer::BotSpec botSpecW = botSpecB;
          gameData = gameRunner->runGame(
            seed, botSpecB, botSpecW, forkData, NULL, logger,
            shouldStopFunc,
            shouldPause,
            nullptr,
            nullptr,
            nullptr
          );
          logger.write(
            "Game #" + Global::int64ToString(gameIdx) +
            " selfplay W - B score: " +
            Global::floatToString(gameData->finalWhiteMinusBlackScore()) +
            "; adv_" + curAdvSearchParams.getSearchAlgoAsStr() +
                "@" + Global::intToString(curAdvSearchParams.maxVisits)
          );
        }
      } else {
        manager->countOneGameStarted(nnEval);
        MatchPairer::BotSpec botSpecB;
        botSpecB.botIdx = 0;
        botSpecB.botName = nnEval->getModelName();
        botSpecB.nnEval = nnEval;
        botSpecB.baseParams = baseParams;
        MatchPairer::BotSpec botSpecW = botSpecB;

        string seed = gameSeedBase + ":" + Global::uint64ToHexString(thisLoopSeedRand.nextUInt64());
        gameData = gameRunner->runGame(
          seed, botSpecB, botSpecW, forkData, NULL, logger,
          shouldStopFunc,
          shouldPause,
          (switchNetsMidGame ? checkForNewNNEval : nullptr),
          nullptr,
          nullptr
        );
      }

      //NULL gamedata will happen when the game is interrupted by shouldStop, which means we should also stop.
      //Or when we run out of total games.
      bool shouldContinue = gameData != NULL;
      //Note that if we've gotten a newNNEval, we're actually pushing the game as data for the new one, rather than the old one!
      if(gameData != NULL)
        manager->enqueueDataToWrite(nnEval,gameData);

      manager->release(nnEval);
      curVictimNNEval.reset();

      if(!shouldContinue)
        break;
    }

    logger.write(logPrefix + "terminating");
  };
  auto gameLoopProtected = [&logger,&gameLoop](int threadIdx) {
    Logger::logThreadUncaught("game loop", &logger, [&](){ gameLoop(threadIdx); });
  };

  //Looping thread for polling for new neural nets and loading them in
  std::mutex modelLoadMutex;
  std::condition_variable modelLoadSleepVar;
  auto modelLoadLoop = [&modelLoadMutex,&modelLoadSleepVar,&logger,&manager,&loadLatestNeuralNetIntoManager]() {
    logger.write("Model loading loop thread starting");

    while(true) {
      if(shouldStop.load())
        break;
      string lastNetName = manager->getLatestModelName();
      bool success = loadLatestNeuralNetIntoManager(&lastNetName);
      (void)success;

      if(shouldStop.load())
        break;

      //Sleep for a while and then re-poll
      std::unique_lock<std::mutex> lock(modelLoadMutex);
      modelLoadSleepVar.wait_for(lock, std::chrono::seconds(20), [](){return shouldStop.load();});
    }

    logger.write("Model loading loop thread terminating");
  };
  auto modelLoadLoopProtected = [&logger,&modelLoadLoop]() {
    Logger::logThreadUncaught("model load loop", &logger, modelLoadLoop);
  };

  vector<std::thread> threads;
  for(int i = 0; i<numGameThreads; i++) {
    threads.push_back(std::thread(gameLoopProtected,i));
  }
  std::thread modelLoadLoopThread(modelLoadLoopProtected);

  //Wait for all game threads to stop
  for(int i = 0; i<threads.size(); i++)
    threads[i].join();

  //If by now somehow shouldStop is not true, set it to be true since all game threads are toast
  shouldStop.store(true);

  //Wake up the model loading thread rather than waiting for it to wake up on its own, and
  //wait for it to die.
  {
    //Lock so that we don't race where we notify the loading thread to wake when it's still in
    //its own critical section but not yet slept, and to ensure the two agree on shouldStop.
    std::lock_guard<std::mutex> lock(modelLoadMutex);
    modelLoadSleepVar.notify_all();
  }
  modelLoadLoopThread.join();

  singleVictim.reset();
  // no actual deallocation, just tidying up the vector
  victimNNEvals.clear();

  //At this point, nothing else except possibly data write loops are running, within the selfplay manager.
  delete manager;

  //Delete and clean up everything else
  NeuralNet::globalCleanup();
  delete forkData;
  delete gameRunner;
  ScoreValue::freeTables();

  if(sigReceived.load())
    logger.write("Exited cleanly after signal");
  logger.write("All cleaned up, quitting");
  return 0;
}
