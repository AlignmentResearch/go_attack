#include "../core/global.h"
#include "../core/config_parser.h"
#include "../core/fileutils.h"
#include "../dataio/sgf.h"
#include "../search/asyncbot.h"
#include "../program/setup.h"
#include "../program/playutils.h"
#include "../tests/tests.h"
#include "../command/commandline.h"
#include "../main.h"

#include <chrono>
#include <map>
#include <sstream>
#include <fstream>

using namespace std;


int MainCmds::testgpuerror(const vector<string>& args) {
  Board::initHash();
  ScoreValue::initTables();
  Rand seedRand;

  ConfigParser cfg;
  string modelFile;
  int boardSize;
  bool quickTest;
  try {
    KataGoCommandLine cmd("Benchmark with gtp config to test speed with different numbers of threads.");
    cmd.addConfigFileArg(KataGoCommandLine::defaultGtpConfigFileName(),"gtp_example.cfg");
    cmd.addModelFileArg();
    TCLAP::ValueArg<int> boardSizeArg("","boardsize", "Size of board to benchmark on (9,13,19), default 19", false, 19, "SIZE");
    TCLAP::SwitchArg quickArg("","quick","Faster shorter test");
    cmd.add(boardSizeArg);
    cmd.add(quickArg);

    cmd.setShortUsageArgLimit();
    cmd.addOverrideConfigArg();

    cmd.parseArgs(args);

    modelFile = cmd.getModelFile();
    boardSize = boardSizeArg.getValue();
    quickTest = quickArg.getValue();
    cmd.getConfig(cfg);

    if(boardSize != 19 && boardSize != 13 && boardSize != 9)
      throw StringError("Board size to test: invalid value " + Global::intToString(boardSize));
  }
  catch (TCLAP::ArgException &e) {
    cerr << "Error: " << e.error() << " for argument " << e.argId() << endl;
    return 1;
  }

  const bool logToStdoutDefault = true;
  const bool logToStderrDefault = false;
  const bool logTimeDefault = false;
  Logger logger(NULL, logToStdoutDefault, logToStderrDefault, logTimeDefault);
  logger.write("Testing average errors between different GPU configurations...");

  const string expectedSha256 = "";
  int maxBatchSize;
  if(cfg.contains("nnMaxBatchSize")) {
    maxBatchSize = cfg.getInt("nnMaxBatchSize", 1, 65536);
    logger.write("For batch test, using batch size from nnMaxBatchSize in config: " + Global::intToString(maxBatchSize));
  }
  else if(cfg.contains("numSearchThreads")) {
    maxBatchSize = cfg.getInt("numSearchThreads", 1, 65536);
    logger.write("For batch test, using batch size from numSearchThreads in config: " + Global::intToString(maxBatchSize));
  }
  else {
    maxBatchSize = 16;
    logger.write("For batch test, using default batch size 16");
  }
  const int maxConcurrentEvals = maxBatchSize * 2 + 16;
  const int expectedConcurrentEvals = maxBatchSize * 2 + 16;
  const bool defaultRequireExactNNLen = false;

  NNEvaluator* nnEval;
  NNEvaluator* nnEval32;
  {
    logger.write("Initializing nneval using current config...");
    const bool disableFP16 = false;
    nnEval = Setup::initializeNNEvaluator(
      modelFile,modelFile,expectedSha256,cfg,logger,seedRand,maxConcurrentEvals,expectedConcurrentEvals,
      boardSize,boardSize,maxBatchSize,defaultRequireExactNNLen,disableFP16,
      Setup::SETUP_FOR_BENCHMARK
    );
  }
  {
    if(nnEval->isAnyThreadUsingFP16()) {
      logger.write("Initializing nneval in fp32...");
      const bool disableFP16 = true;
      nnEval32 = Setup::initializeNNEvaluator(
        modelFile,modelFile,expectedSha256,cfg,logger,seedRand,maxConcurrentEvals,expectedConcurrentEvals,
        boardSize,boardSize,maxBatchSize,defaultRequireExactNNLen,disableFP16,
        Setup::SETUP_FOR_BENCHMARK
      );
    }
    else {
      nnEval32 = nnEval;
    }
  }

  const int maxBatchSizeCap = -1;
  const bool verbose = true;
  bool fp32BatchSuccessBuf = true;
  bool success = Tests::runFP16Test(nnEval,nnEval32,logger,boardSize,maxBatchSizeCap,verbose,quickTest,fp32BatchSuccessBuf);
  (void)success;
  // cout << success << endl;

  if(nnEval32 != nnEval)
    delete nnEval32;
  delete nnEval;
  NeuralNet::globalCleanup();
  ScoreValue::freeTables();

  return 0;
}
