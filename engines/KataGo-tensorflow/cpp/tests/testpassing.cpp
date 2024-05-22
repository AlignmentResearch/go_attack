#include "../core/config_parser.h"
#include "../dataio/sgf.h"
#include "../search/search.h"
#include "../tests/testamcts.h"
#include "../tests/tests.h"

using namespace std;
using namespace TestCommon;

static SearchParams customSearchParams(const int maxVisits,
                                       const SearchParams::PassingBehavior pb) {
  SearchParams searchParams;
  searchParams.maxVisits = maxVisits;
  searchParams.passingBehavior = pb;
  return searchParams;
}

static void setupBot(Search& bot) {
  AMCTSTests::resetBot(bot, 7, Rules::getTrompTaylorish());

  // The base 7x7 board we perform tests on.
  // It has the following layout (with white to move):
  // Black - X ; White - O
  //
  //        A B C D E F G
  //      7 X X X X O O O
  //      6 . . X X O . .
  //      5 X X X X O O O
  //      4 X X X X O O O
  //      3 X X X O O O O
  //      2 X X X O O O O
  //      1 . . X O O . .
  //
  const unique_ptr<CompactSgf> initSgf(CompactSgf::parse(
      "(;GM[1]FF[4]CA[UTF-8]AP[Sabaki:0.52.2]KM[6.5]SZ[7]DT[2022-12-15];B[aa];"
      "W[ga];B[ba];W[fa];B[ca];W[ea];B[cb];W[eb];B[cc];W[ec];B[cd];W[ed];B[ce];"
      "W[ee];B[cf];W[ef];B[cg];W[eg];B[ac];W[gc];B[bc];W[fc];B[ad];W[gd];B[bd];"
      "W[fd];B[ae];W[ge];B[be];W[fe];B[af];W[gf];B[bf];W[ff];B[da];W[dg];B[db];"
      "W[df];B[dc];W[de];B[dd])"));
  for (auto& m : initSgf->moves) {
    bot.makeMove(m.loc, m.pla);
  }
}

// Checks the contents of two vectors are equal, ignoring order
template <typename T>
static void assertContentsEqual(const vector<T>& a, const vector<T>& b) {
  testAssert(a.size() == b.size());
  set<T> sa(a.begin(), a.end());
  set<T> sb(b.begin(), b.end());
  testAssert(sa == sb);
}

static void checkPositiveWeightMoves(Search& bot,
                                     const vector<string>& expectedMoves) {
  vector<Loc> locs;
  vector<double> playSelectionValues;
  bool suc = bot.getPlaySelectionValues(locs, playSelectionValues, 0);
  testAssert(suc);
  testAssert(locs.size() == playSelectionValues.size());

  vector<string> positiveLocStrs;
  for (int i = 0; i < locs.size(); i++) {
    if (playSelectionValues[i] > 0) {
      positiveLocStrs.push_back(
          Location::toString(locs[i], bot.getRootBoard()));
    }
  }

  assertContentsEqual(positiveLocStrs, expectedMoves);
}

void Tests::runPassingTests() {
  cout << "Running passing tests" << endl;

  ConfigParser cfg(AMCTSTests::AMCTS_CONFIG_PATH);
  Logger logger(&cfg);

  // Passing /dev/null triggers debugSkipNeuralNet=true,
  // which makes nnEvalRand a random policy
  auto nnEvalRand = AMCTSTests::getNNEval("/dev/null", cfg, logger, 42);

  // Test Standard passing behavior
  {
    const auto pb = SearchParams::PassingBehavior::Standard;
    Search bot1(customSearchParams(1, pb), nnEvalRand.get(), &logger,
                "forty-two");
    Search bot2(customSearchParams(10000, pb), nnEvalRand.get(), &logger,
                "forty-two");
    for (auto bot_ptr : {&bot1, &bot2}) {
      Search& bot = *bot_ptr;

      // Setup board and run search
      setupBot(bot);
      bot.runWholeSearchAndGetMove(P_WHITE);

      // Check search results are as expected
      checkPositiveWeightMoves(
          bot, {"A1", "B1", "F1", "G1", "A6", "B6", "F6", "G6", "pass"});
    }
  }

  // Test AvoidPassAliveTerritory
  {
    const auto pb = SearchParams::PassingBehavior::AvoidPassAliveTerritory;
    Search bot1(customSearchParams(1, pb), nnEvalRand.get(), &logger,
                "forty-two");
    Search bot2(customSearchParams(10000, pb), nnEvalRand.get(), &logger,
                "forty-two");
    for (auto bot_ptr : {&bot1, &bot2}) {
      Search& bot = *bot_ptr;

      // Setup board and run search
      setupBot(bot);
      bot.runWholeSearchAndGetMove(P_WHITE);

      // Check search results are as expected
      checkPositiveWeightMoves(bot, {"A1", "B1", "A6", "B6"});
    }
  }

  // Test AvoidPassAliveTerritory when policy puts zero weight on legal moves
  {
    const auto pb = SearchParams::PassingBehavior::AvoidPassAliveTerritory;
    Search bot(customSearchParams(1, pb), nnEvalRand.get(), &logger,
               "forty-two");

    // Setup board and run search
    setupBot(bot);
    bot.runWholeSearchAndGetMove(P_WHITE);

    // Now manually modify the policy to put zero weight on A1, B1, A6, B6
    NNOutput* nnOutput = bot.rootNode->nnOutput.load()->get();
    set<string> legalMoves{"A1", "B1", "A6", "B6"};
    for (int movePos = 0; movePos < bot.policySize; movePos++) {
      const Loc moveLoc =
          NNPos::posToLoc(movePos, bot.rootBoard.x_size, bot.rootBoard.y_size,
                          bot.nnXLen, bot.nnYLen);
      const string moveLocStr = Location::toString(moveLoc, bot.rootBoard);

      if (legalMoves.count(moveLocStr) > 0) {
        nnOutput->policyProbs[movePos] = -1e9;
      }
    }

    // Check search results are as expected
    checkPositiveWeightMoves(bot, {"pass"});
  }
}
