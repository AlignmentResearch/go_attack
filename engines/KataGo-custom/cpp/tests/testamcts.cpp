#include "../tests/testamcts.h"

#include "../dataio/sgf.h"
#include "../program/play.h"
#include "../program/setup.h"
#include "../tests/tests.h"

using namespace std;

// Uncomment to enable debugging
// #define DEBUG

void AMCTSTests::runAllAMCTSTests(const int maxVisits,
                                  const int numMovesToSimulate) {
  testConstPolicies();
  testMCTS(maxVisits, numMovesToSimulate);
  testAMCTS(maxVisits, numMovesToSimulate);
}

static constexpr double TOTALCHILDWEIGHT_PUCT_OFFSET = 0.01;

static bool approxEqual(float x, float y) {
  float tolerance;
  tolerance = 0.0001f * std::max(std::abs(x), std::max(std::abs(y), 1.0f));
  return std::abs(x - y) < tolerance;
}

static bool approxEqual(double x, double y) {
  double tolerance;
  tolerance = 1e-5 * std::max(std::abs(x), std::max(std::abs(y), 1.0));
  return std::abs(x - y) < tolerance;
}

static bool approxEqual(const NodeStats& s1, const NodeStats& s2) {
  // When total weight is zero, we just check weights match.
  if (s1.weightSum == 0)
    return s2.weightSum == 0 && s1.weightSqSum == 0 && s2.weightSqSum == 0;

  return approxEqual(s1.winLossValueAvg, s2.winLossValueAvg) &&
         approxEqual(s1.noResultValueAvg, s2.noResultValueAvg) &&
         approxEqual(s1.scoreMeanAvg, s2.scoreMeanAvg) &&
         approxEqual(s1.scoreMeanSqAvg, s2.scoreMeanSqAvg) &&
         approxEqual(s1.leadAvg, s2.leadAvg) &&
         approxEqual(s1.utilityAvg, s2.utilityAvg) &&
         approxEqual(s1.utilitySqAvg, s2.utilitySqAvg) &&
         approxEqual(s1.weightSum, s2.weightSum) &&
         approxEqual(s1.weightSqSum, s2.weightSqSum);
}

// Sets SearchParams in a such a way that makes checking (A)MCTS easy.
static void setSimpleSearchParams(SearchParams& params) {
  // Force bot to weight purely by visits for tests.
  // https://discord.com/channels/417022162348802048/583775968804732928/698893048049827870
  params.valueWeightExponent = 0;

  // We turn off subtree utility bias correction so backup is easier to check.
  // https://github.com/lightvector/KataGo/blob/master/docs/KataGoMethods.md#subtree-value-bias-correction
  params.subtreeValueBiasFactor = 0;

  // Disable rootNoise so playouts are deterministic and can be checked.
  params.rootNoiseEnabled = false;

  // Disable rootEndingBonusPoints to remove complex hand-engineered scoring
  // adjustment.
  params.rootEndingBonusPoints = 0;

  // TODO(tony): Support this within the playout check.
  params.rootDesiredPerChildVisitsCoeff = 0;

  // This is not used in selfplay right now for backwards compatibility
  // reasons?!?
  params.useNonBuggyLcb = true;

  testAssert(params.cpuctExplorationLog == 0);
  testAssert(params.cpuctUtilityStdevScale == 0);
  testAssert(params.wideRootNoise == 0);
  testAssert(params.fpuParentWeight == 0);
  testAssert(!params.useNoisePruning);
  testAssert(!params.useUncertainty);
  testAssert(!params.antiMirror);
  testAssert(!params.forceWinningPass);  // We aren't testing pass sharpening.
}

// Computes the fpuValue of a node with overriden stats and visits.
// This is needed in checkPlayoutLogic to simulate the tree-search process,
// since node contains stats from the completed search tree. During simulation
// we need to get the fpuValue of a node in a partially re-simulated tree.
static double getFpuValue(const Search& bot, const SearchNode* node,
                          const NodeStats& statOverride,
                          const int64_t visitOverride,
                          double policyProbMassVisited) {
  // We create a dummy SearchNode and set
  //    {node->nnOutput, statOverride, visitOverride}.
  // This is a bit hacky, but saves on code duplication, which is more important
  // for these tests.

  const Player prevPla = getOpp(node->nextPla);
  SearchNode dummyNode(prevPla, node->forceNonTerminal, node->mutexIdx);

  // Set nnEval -- remember to unset later because dummyNode will delete it
  dummyNode.storeNNOutputIfNull(node->nnOutput);

  // Set stats
  dummyNode.stats = statOverride;

  // Set visits
  dummyNode.stats.visits = visitOverride;

  const bool isRoot = node == bot.rootNode;
  double _, __, ___;  // throwaways, though need to be distinct
  const double fpuValue = bot.getFpuValueForChildrenAssumeVisited(
      dummyNode, node->nextPla, isRoot, policyProbMassVisited, _, __, ___);

  // Unset nnEval
  dummyNode.nnOutput = nullptr;

  return fpuValue;
}

void AMCTSTests::testConstPolicies() {
  cout << "Testing custom const policy nets..." << endl;

  ConfigParser cfg(AMCTS_CONFIG_PATH);
  Logger logger(&cfg, false);

  testAssert(parseRules(cfg, logger) == Rules::getTrompTaylorish());

  vector<SearchParams> searchParamss =
      Setup::loadParams(cfg, Setup::SETUP_FOR_OTHER);
  testAssert(searchParamss.size() == 2);

  SearchParams mctsParams = searchParamss[0];
  mctsParams.maxVisits = 1;
  {  // Remove all randomness from policy.
    mctsParams.chosenMoveTemperatureEarly = 0;
    mctsParams.chosenMoveTemperature = 0;
    mctsParams.rootNoiseEnabled = false;
  }

  auto nnEval1 = getNNEval(CONST_POLICY_1_PATH, cfg, logger, 42);
  auto nnEval2 = getNNEval(CONST_POLICY_2_PATH, cfg, logger, 42);

  {  // Check argmax-bot1 policy
    Search bot1(mctsParams, nnEval1.get(), &logger, "forty-two");

    for (int board_size : {5, 6, 7, 19}) {
      resetBot(bot1, board_size, Rules::getTrompTaylorish());
      Player pla = P_BLACK;
      for (int i = 0; i < 3 * board_size + 3; i++) {
        const Loc loc = bot1.runWholeSearchAndGetMove(pla);
        testAssert(loc != Board::PASS_LOC);

        if (i < bot1.rootBoard.x_size) {
          testAssert(Location::getX(loc, bot1.rootBoard.x_size) == i);
          testAssert(Location::getY(loc, bot1.rootBoard.x_size) == 0);
        }

        testAssert(bot1.makeMove(loc, pla));
        pla = getOpp(pla);
      }
    }
  }

  {  // Check argmax-bot1 and argmax-bot2 interaction.
    Search bot1(mctsParams, nnEval1.get(), &logger, "forty-two");
    Search bot2(mctsParams, nnEval2.get(), &logger, "forty-two");

    const int BOARD_SIZE = 7;
    resetBot(bot1, BOARD_SIZE, Rules::getTrompTaylorish());
    resetBot(bot2, BOARD_SIZE, Rules::getTrompTaylorish());

    testAssert(bot1.rootHistory.rules.multiStoneSuicideLegal);
    testAssert(bot1.rootHistory.rules.koRule == Rules::KO_POSITIONAL);

    Player pla = P_BLACK;
    for (int i = 0; i < 2 * 7 * 7; i++) {
      const Loc loc = i % 2 == 0 ? bot1.runWholeSearchAndGetMove(pla)
                                 : bot2.runWholeSearchAndGetMove(pla);

      if (i % 2 == 0) {  // bot1 (black) move
        if (i / 2 < 7 * 7 - 1) {
          testAssert(Location::getX(loc, 7) == (i / 2) % 7);
          testAssert(Location::getY(loc, 7) == (i / 2) / 7);
        } else {
          testAssert(loc == Board::PASS_LOC);  // Pass due to superko
        }
      } else {  // bot2 (white) move
        testAssert(loc == Board::PASS_LOC);
      }

      {
        auto buf = evaluate(nnEval1, bot1.rootBoard, bot1.rootHistory, pla);
        testAssert(approxEqual(buf->result->whiteWinProb,
                               pla == P_WHITE ? CP1_WIN_PROB : CP1_LOSS_PROB));
        testAssert(approxEqual(buf->result->whiteLossProb,
                               pla == P_WHITE ? CP1_LOSS_PROB : CP1_WIN_PROB));
        testAssert(approxEqual(buf->result->whiteNoResultProb, 0));
      }

      {
        auto buf = evaluate(nnEval2, bot1.rootBoard, bot1.rootHistory, pla);
        testAssert(approxEqual(buf->result->whiteWinProb,
                               pla == P_WHITE ? CP2_WIN_PROB : CP2_LOSS_PROB));
        testAssert(approxEqual(buf->result->whiteLossProb,
                               pla == P_WHITE ? CP2_LOSS_PROB : CP2_WIN_PROB));
        testAssert(approxEqual(buf->result->whiteNoResultProb, 0));
      }

      testAssert(bot1.makeMove(loc, pla));
      testAssert(bot2.makeMove(loc, pla));
      pla = getOpp(pla);
    }

    testAssert(bot1.rootHistory.isGameFinished);
    testAssert(bot2.rootHistory.isGameFinished);
  }
}

void AMCTSTests::testMCTS(const int maxVisits, const int numMovesToSimulate) {
  cout << "Testing MCTS..." << endl;

  ConfigParser cfg(AMCTS_CONFIG_PATH);
  Logger logger(&cfg, false);

  vector<SearchParams> searchParamss =
      Setup::loadParams(cfg, Setup::SETUP_FOR_OTHER);
  testAssert(searchParamss.size() == 2);

  const SearchParams mctsParams = [&]() {
    // searchParamss[0] is MCTS, searchParamss[1] is AMCTS; copy the 0th.
    SearchParams ret = searchParamss[0];
    setSimpleSearchParams(ret);
    return ret;
  }();

  auto nnEval1 = getNNEval(CONST_POLICY_1_PATH, cfg, logger, 42);
  auto nnEval2 = getNNEval(CONST_POLICY_2_PATH, cfg, logger, 42);
  Search bot1(mctsParams, nnEval1.get(), &logger, "forty-two");
  Search bot2(mctsParams, nnEval2.get(), &logger, "forty-two");

  for (auto bot_ptr : {&bot1, &bot2}) {
    Search& bot = *bot_ptr;

    const int BOARD_SIZE = 9;
    resetBot(bot, BOARD_SIZE, Rules::getTrompTaylorish());

    // The initial board we perform tests on.
    // It has 8 placed stones that are at the top left corner that look like
    // this:
    //    BBBB.....
    //    .WWWW....
    //    .........
    // Here, dots are empty spaces. It is black's turn to move.
    const unique_ptr<CompactSgf> initSgf(
        CompactSgf::parse("(;FF[4]KM[7.5]SZ[19];B[aa];W[bb];B[ba];W[cb];B[ca];"
                          "W[db];B[da];W[eb])"));
    for (auto& m : initSgf->moves) {
      bot.makeMove(m.loc, m.pla);
    }

    Player curPla = P_BLACK;
    for (int midx = 0; midx < numMovesToSimulate; midx++) {
      // Change up visit count to make tests more varied
      bot.searchParams.maxVisits = maxVisits + midx;

      bot.clearSearch();
      const Loc loc = bot.runWholeSearchAndGetMove(curPla);

      checkMCTSSearch(bot, (&bot == &bot1) ? CP1_WIN_PROB : CP2_WIN_PROB,
                      (&bot == &bot1) ? CP1_LOSS_PROB : CP2_LOSS_PROB);

      bot.makeMove(loc, curPla);
      curPla = getOpp(curPla);

      // Break if game is finished.
      if (bot.rootHistory.isGameFinished) break;
    }
  }
}

void AMCTSTests::testAMCTS(const int maxVisits, const int numMovesToSimulate) {
  cout << "Testing AMCTS..." << endl;

  ConfigParser cfg(AMCTS_CONFIG_PATH);
  Logger logger(&cfg, false);

  vector<SearchParams> searchParamss =
      Setup::loadParams(cfg, Setup::SETUP_FOR_OTHER);
  testAssert(searchParamss.size() == 2);

  const auto getMctsParams = [&](const bool useGraphSearch) {
    SearchParams ret = searchParamss[0];
    setSimpleSearchParams(ret);

    // Make opponent MCTS deterministic for easy testing
    ret.chosenMoveTemperature = 0;
    ret.chosenMoveTemperatureEarly = 0;

    ret.useGraphSearch = useGraphSearch;

    return ret;
  };

  const SearchParams amcts_s_Params = [&]() {
    SearchParams ret = searchParamss[1];
    ret.searchAlgo = SearchParams::SearchAlgorithm::AMCTS_S;
    setSimpleSearchParams(ret);
    return ret;
  }();
  const SearchParams amcts_r_Params = [&]() {
    SearchParams ret = amcts_s_Params;
    ret.searchAlgo = SearchParams::SearchAlgorithm::AMCTS_R;
    return ret;
  }();

  auto nnEval1 =
      getNNEval(CONST_POLICY_1_PATH, cfg, logger, 42);  // move over pass
  auto nnEval2 =
      getNNEval(CONST_POLICY_2_PATH, cfg, logger, 42);  // pass over move
  Search bot11_s(amcts_s_Params, nnEval1.get(), &logger, "forty-two",
                 getMctsParams(false), nnEval1.get());
  Search bot12_s(amcts_s_Params, nnEval1.get(), &logger, "forty-two",
                 getMctsParams(true), nnEval2.get());

  Search bot11_r(amcts_r_Params, nnEval1.get(), &logger, "forty-two",
                 getMctsParams(true), nnEval1.get());
  Search bot12_r(amcts_r_Params, nnEval1.get(), &logger, "forty-two",
                 getMctsParams(false), nnEval2.get());

  for (auto bot_ptr : {&bot11_s, &bot12_s, &bot11_r, &bot12_r}) {
    Search& bot = *bot_ptr;

    const int BOARD_SIZE = 9;
    resetBot(bot, BOARD_SIZE, Rules::getTrompTaylorish());

    // The initial board we perform tests on.
    // It has 8 placed stones that are at the top left corner that look like
    // this:
    //    BBBB.....
    //    .WWWW....
    //    .........
    // Here, dots are empty spaces. It is black's turn to move.
    const unique_ptr<CompactSgf> initSgf(
        CompactSgf::parse("(;FF[4]KM[7.5]SZ[19];B[aa];W[bb];B[ba];W[cb];B[ca];"
                          "W[db];B[da];W[eb])"));
    for (auto& m : initSgf->moves) {
      bot.makeMove(m.loc, m.pla);
    }

    Player curPla = P_BLACK;
    for (int midx = 0; midx < numMovesToSimulate; midx++) {
      // Change up visit count to make tests more varied
      bot.searchParams.maxVisits =
          (maxVisits / bot.oppBot.get()->searchParams.maxVisits) + midx;

      bot.clearSearch();
      const Loc loc = bot.runWholeSearchAndGetMove(curPla);

      if (&bot == &bot11_s || &bot == &bot11_r) {
        checkAMCTSSearch(bot, CP1_WIN_PROB, CP1_LOSS_PROB, CP1_WIN_PROB,
                         CP1_LOSS_PROB);
      } else if (&bot == &bot12_s || &bot == &bot12_r) {
        checkAMCTSSearch(bot, CP1_WIN_PROB, CP1_LOSS_PROB, CP2_WIN_PROB,
                         CP2_LOSS_PROB);
      }

      bot.makeMove(loc, curPla);
      curPla = getOpp(curPla);

      // Make sure game hasn't been prematurely ended.
      testAssert(!bot.rootHistory.isGameFinished);
    }
  }
}

void AMCTSTests::checkMCTSSearch(const Search& bot, const float win_prob,
                                 const float loss_prob) {
  testAssert(bot.searchParams.searchAlgo ==
             SearchParams::SearchAlgorithm::MCTS);
  SearchTree tree(bot);

  // Not equality since sometimes we visit terminal nodes multiple times.
  testAssert(tree.all_nodes.size() <= bot.searchParams.maxPlayouts);

  // Test { nodes without nnOutputs } == { terminal nodes }
  for (auto node : tree.all_nodes) {
    if (node->getNNOutput() == nullptr) {
      assert(tree.getNodeHistory(node).isGameFinished);
    } else {
      assert(!tree.getNodeHistory(node).isGameFinished);
    }
  }

  // Test weights are as expected
  for (auto node : tree.all_nodes) {
    if (node->getNNOutput() == nullptr) {
      // Terminal nodes don't have a nnoutput, so we directly check
      // weightSum. They might also be visited more than once.
      testAssert(NodeStats(node->stats).weightSum >= 1);
    } else {
      testAssert(bot.computeWeightFromNode(*node) == 1);
    }
  }

  // Test nnOutputs are as expected
  for (auto node : tree.all_nodes) {
    if (node->getNNOutput() == nullptr) continue;
    testAssert(approxEqual(node->getNNOutput()->whiteWinProb,
                           node->nextPla == P_WHITE ? win_prob : loss_prob));
    testAssert(approxEqual(node->getNNOutput()->whiteLossProb,
                           node->nextPla == P_WHITE ? loss_prob : win_prob));
    testAssert(approxEqual(node->getNNOutput()->whiteNoResultProb, 0));
  }

  // Test backup
  for (auto node : tree.all_nodes) {
    const NodeStats s1 = averageStats(bot, tree.getSubtreeNodes(node));
    const NodeStats s2(node->stats);
    testAssert(approxEqual(s1, s2));
  }

  checkFinalMoveSelection(bot);

  checkPlayoutLogic(bot);
}

void AMCTSTests::checkAMCTSSearch(const Search& bot, const float win_prob1,
                                  const float loss_prob1, const float win_prob2,
                                  const float loss_prob2) {
  testAssert(bot.searchParams.usingAdversarialAlgo());

  SearchTree tree(bot);

  // Not equality since sometimes we visit terminal nodes multiple times.
  testAssert(tree.all_nodes.size() <= bot.searchParams.maxPlayouts);

  // Test { nodes without nnOutputs } == { terminal nodes }
  for (auto node : tree.all_nodes) {
    if (node->getNNOutput() == nullptr) {
      testAssert(tree.getNodeHistory(node).isGameFinished);
    } else {
      testAssert(!tree.getNodeHistory(node).isGameFinished);
    }
  }

  // Test weights are as expected
  for (auto node : tree.all_nodes) {
    if (node->getNNOutput() == nullptr) {
      // Terminal nodes don't have a nnOutput, so we directly check
      // weightSum. They might also be visited more than once.
      testAssert(NodeStats(node->stats).weightSum >= 1);
    } else if (node->nextPla == bot.rootPla) {
      testAssert(bot.computeWeightFromNode(*node) == 1);
    } else {
      testAssert(bot.computeWeightFromNode(*node) == 0);
    }
  }

  // Test nnOutputs are as expected
  for (auto node : tree.all_nodes) {
    if (node->getNNOutput() == nullptr) continue;

    if (node->nextPla == bot.rootPla) {  // Adversary node
      const float win_prob =
          (node->nextPla == bot.rootPla) ? win_prob1 : win_prob2;
      const float loss_prob =
          (node->nextPla == bot.rootPla) ? loss_prob1 : loss_prob2;

      testAssert(approxEqual(node->getNNOutput()->whiteWinProb,
                             node->nextPla == P_WHITE ? win_prob : loss_prob));
      testAssert(approxEqual(node->getNNOutput()->whiteLossProb,
                             node->nextPla == P_WHITE ? loss_prob : win_prob));
      testAssert(approxEqual(node->getNNOutput()->whiteNoResultProb, 0));
    } else {  // Victim node
      testAssert(node->oppLocs.has_value());
      testAssert(node->oppPlaySelectionValues.has_value());
    }
  }

  // Test backup
  for (auto node : tree.all_nodes) {
    const NodeStats s1 = averageStats(bot, tree.getSubtreeNodes(node));
    const NodeStats s2(node->stats);
    testAssert(approxEqual(s1, s2));
  }

  checkFinalMoveSelection(bot);

  checkPlayoutLogic(bot);
}

void AMCTSTests::checkFinalMoveSelection(const Search& bot) {
  // We don't test non-standard passing behaviors here.
  testAssert(bot.searchParams.passingBehavior ==
             SearchParams::PassingBehavior::Standard);

  unordered_map<Loc, double> trueLocToPsv;
  {
    vector<double> playSelectionValues;
    vector<Loc> locs;
    bot.getPlaySelectionValues(locs, playSelectionValues, 0);
    for (size_t i = 0; i < playSelectionValues.size(); i++) {
      trueLocToPsv[locs[i]] = playSelectionValues[i];
    }

    testAssert(playSelectionValues.size() == locs.size());
    testAssert(trueLocToPsv.size() == locs.size());
  }

  SearchTree tree(bot);
  unordered_map<const SearchNode*, double> childToPsv;
  {
    testAssert(tree.children.at(tree.root).size() > 0);

    for (const auto child : tree.children.at(tree.root)) {
      const double child_weight =
          averageStats(bot, tree.getSubtreeNodes(child)).weightSum;
      childToPsv[child] = child_weight;
    }

    double totalChildWeight = 0;
    double maxChildWeight = 1e-50;
    const SearchNode* heaviestChild = nullptr;
    for (const auto child : tree.children.at(tree.root)) {
      const double weight = childToPsv[child];
      totalChildWeight += weight;
      if (weight > maxChildWeight) {
        maxChildWeight = weight;
        heaviestChild = child;
      }
    }

    // Possibly reduce weight on children that we spend too many visits on in
    // retrospect.
    // TODO(tony): Figure out what exactly is going on here and write it down on
    // overleaf.
    const float* policyProbs =
        tree.root->getNNOutput()->getPolicyProbsMaybeNoised();
    const double bestChildExploreSelectionValue = [&]() -> double {
      double parentUtility;
      double parentWeightPerVisit;
      double parentUtilityStdevFactor;
      double fpuValue = bot.getFpuValueForChildrenAssumeVisited(
          *tree.root, tree.root->nextPla, true, 1.0, parentUtility,
          parentWeightPerVisit, parentUtilityStdevFactor);
      const double exploreScaling = bot.getExploreScaling(totalChildWeight, parentUtilityStdevFactor);

      return bot.getExploreSelectionValueOfChild(
          *tree.root, policyProbs, heaviestChild,
          tree.revEdge.at(heaviestChild).moveLoc, exploreScaling, totalChildWeight,
          heaviestChild->stats.visits.load(std::memory_order_acquire), fpuValue,
          parentUtility, parentWeightPerVisit, false,
          false, maxChildWeight, NULL);
    }();
    const double exploreScaling = bot.getExploreScaling(totalChildWeight, 1.0);
    for (auto& [child, weight] : childToPsv) {
      if (child == heaviestChild) continue;
      const int64_t visits =
          child->stats.visits.load(std::memory_order_acquire);
      const double reduced = bot.getReducedPlaySelectionWeight(
          *tree.root, policyProbs, child, tree.revEdge.at(child).moveLoc,
          exploreScaling, visits, bestChildExploreSelectionValue);
      weight = ceil(reduced);
    }

    // Adjust psvs with lcb values
    // TODO(tony): Figure out what exactly is going on here and write it down on
    // overleaf.
    testAssert(bot.searchParams.useLcbForSelection);
    testAssert(bot.searchParams.useNonBuggyLcb);
    {
      unordered_map<const SearchNode*, double> lcbs, radii;
      double bestLcb = -1e10;
      const SearchNode* bestLcbChild = nullptr;
      for (const auto child : tree.children.at(tree.root)) {
        const Loc loc = tree.revEdge.at(child).moveLoc;
        const int64_t visits =
            child->stats.visits.load(std::memory_order_acquire);
        bot.getSelfUtilityLCBAndRadius(*tree.root, child, visits, loc,
                                       lcbs[child], radii[child]);
        double weight = childToPsv[child];
        if (weight > 0 &&
            weight >= bot.searchParams.minVisitPropForLCB * maxChildWeight) {
          if (lcbs[child] > bestLcb) {
            bestLcb = lcbs[child];
            bestLcbChild = child;
          }
        }
      }

      if (bestLcbChild != nullptr) {
        double best_bound = childToPsv[bestLcbChild];
        for (auto child : tree.children.at(tree.root)) {
          if (child == bestLcbChild) continue;

          const double excessValue = bestLcb - lcbs[child];
          if (excessValue < 0) continue;

          const double radius = radii[child];
          const double radiusFactor =
              (radius + excessValue) / (radius + 0.20 * excessValue);

          double lbound = radiusFactor * radiusFactor * childToPsv[child];
          if (lbound > best_bound) best_bound = lbound;
        }
        childToPsv[bestLcbChild] = best_bound;
      }
    }

    // Prune
    testAssert(bot.searchParams.chosenMoveSubtract == 0);
    double maxPsv = -1e50;
    for (const auto& [_, psv] : childToPsv) maxPsv = max(maxPsv, psv);
    for (auto& [_, psv] : childToPsv) {
      if (psv < min(bot.searchParams.chosenMovePrune, maxPsv / 64)) {
        psv = 0;
      }
    }
  }

  testAssert(childToPsv.size() == trueLocToPsv.size());
  for (const auto [child, psv] : childToPsv) {
    const Loc loc = tree.revEdge.at(child).moveLoc;
    testAssert(approxEqual(trueLocToPsv[loc], psv));
  }
}

void AMCTSTests::checkPlayoutLogic(const Search& bot) {
  if (bot.searchParams.usingAdversarialAlgo()) {
    // We need temperature to be zero for opponent to be determinstic.
    testAssert(bot.oppBot.get()->searchParams.chosenMoveTemperature == 0);
    testAssert(bot.oppBot.get()->searchParams.chosenMoveTemperatureEarly == 0);
  }

  SearchTree tree(bot);

  unordered_map<const SearchNode*, int> visits;
  auto filterToVisited = [&](const vector<const SearchNode*>& nodes) {
    vector<const SearchNode*> ret;
    for (auto node : nodes) {
      if (visits[node] > 0) ret.push_back(node);
    }
    return ret;
  };

  auto nodeToPos = [&](const SearchNode* node) {
    return NNPos::locToPos(tree.revEdge.at(node).moveLoc, bot.rootBoard.x_size,
                           bot.nnXLen, bot.nnYLen);
  };

  auto averageVisSubtreeStats = [&](const SearchNode* node) {
    return averageStats(bot, filterToVisited(tree.getSubtreeNodes(node)),
                        &visits);
  };

  // Cache for which moves the opponent makes at opponent nodes.
  unordered_map<const SearchNode*, const SearchNode*> oppNodeCache;

#ifdef DEBUG
  auto checkOnePlayout = [&](const bool is_last_playout) -> int {
#else
  auto checkOnePlayout = [&]() -> int {
#endif
    int numNodesAdded = 1;
    Board board = bot.rootBoard;
    BoardHistory history = bot.rootHistory;
    auto helper = [&](const SearchNode* node, auto&& dfs) -> void {
      testAssert(node != nullptr);
      visits[node] += 1;

#ifdef DEBUG
      if (is_last_playout) {
        cout << "DFS Currently at node: " << node << endl;
        cout << "Children:";
        for (auto child : tree.children.at(node)) {
          const Loc loc =
              NNPos::posToLoc(nodeToPos(child), bot.rootBoard.x_size,
                              bot.rootBoard.y_size, bot.nnXLen, bot.nnYLen);
          const string locString = Location::toString(loc, bot.rootBoard);
          cout << " (" << child << ", " << locString << ", " << visits[child]
               << ")";
        }
        cout << endl;
      }
#endif

      if (node->getNNOutput() == nullptr) return;  // This is a terminal nodes
      if (visits[node] == 1) {  // First time visiting the node
        if (bot.searchParams.usingAdversarialAlgo()) {
          if (node->nextPla == bot.rootPla) return;

          numNodesAdded += 1;
          for (auto x : tree.getPathToRoot(node)) visits[x] += 1;
        } else if (bot.searchParams.searchAlgo ==
                   SearchParams::SearchAlgorithm::MCTS) {
          return;
        } else {
          ASSERT_UNREACHABLE;
        }
      }

      if (node != tree.root) {
        history.makeBoardMoveAssumeLegal(board, tree.revEdge.at(node).moveLoc,
                                         getOpp(node->nextPla),
                                         bot.rootKoHashTable);
      }

      const float* policyProbs =
          node->getNNOutput()->getPolicyProbsMaybeNoised();

      const NodeStats nodeStats = averageVisSubtreeStats(node);
      const double totalChildWeight =
          nodeStats.weightSum - bot.computeWeightFromNode(*node);

      vector<const SearchNode*> movePosNode(bot.policySize, nullptr);
      for (auto child : tree.children.at(node)) {
        movePosNode[nodeToPos(child)] = child;
      }

      vector<bool> movePosVis(bot.policySize, false);
      double policyProbMassVisited = 0;
      for (auto child : filterToVisited(tree.children.at(node))) {
        movePosVis[nodeToPos(child)] = true;
        policyProbMassVisited += policyProbs[nodeToPos(child)];
      }

      if (bot.searchParams.usingAdversarialAlgo() &&
          node->nextPla != bot.rootPla) {
        if (oppNodeCache.find(node) == oppNodeCache.end()) {
          bot.oppBot.get()->setPosition(node->nextPla, board, history);
          const Loc loc =
              bot.oppBot.get()->runWholeSearchAndGetMove(node->nextPla);
          const int bestMovePos = NNPos::locToPos(loc, bot.rootBoard.x_size,
                                                  bot.nnXLen, bot.nnYLen);

          oppNodeCache[node] = movePosNode[bestMovePos];
        }

        return dfs(oppNodeCache.at(node), dfs);
      }

#ifdef DEBUG
      vector<tuple<double, double, int>> vals_debug;
#endif

      // These track which child we will descend into.
      int bestMovePos = -1;
      double maxSelectionValue = -1e50;
      auto considerMove = [&](const int pos, const double childWeight,
                              const double whiteUtility) {
        const double nnPolicyProb = policyProbs[pos];
        const double valueComponent =
            node->nextPla == P_WHITE ? whiteUtility : -whiteUtility;
        const double exploreComponent =
            bot.searchParams.cpuctExploration * nnPolicyProb *
            sqrt(totalChildWeight + TOTALCHILDWEIGHT_PUCT_OFFSET) /
            (1.0 + childWeight);

        const double selectionValue =
            nnPolicyProb >= 0 ? valueComponent + exploreComponent
                              : Search::POLICY_ILLEGAL_SELECTION_VALUE;
        if (selectionValue > maxSelectionValue) {
          maxSelectionValue = selectionValue;
          bestMovePos = pos;
        }

#ifdef DEBUG
        vals_debug.push_back({selectionValue, nnPolicyProb, pos});
#endif
      };

      // Try all existing children
      for (const auto child : filterToVisited(tree.children.at(node))) {
        const NodeStats childStats = averageVisSubtreeStats(child);
        considerMove(nodeToPos(child), childStats.weightSum,
                     childStats.utilityAvg);
      }

      // Try unvisited children
      const double fpuValue =
          getFpuValue(bot, node, averageVisSubtreeStats(node), visits[node],
                      policyProbMassVisited);
      for (int pos = 0; pos < bot.policySize; pos++) {
        if (movePosVis[pos]) continue;  // Skip moves that are visited

        // Only consider moves that are valid.
        {
          const Loc loc =
              NNPos::posToLoc(pos, bot.rootBoard.x_size, bot.rootBoard.y_size,
                              bot.nnXLen, bot.nnYLen);
          if (loc == Board::NULL_LOC) continue;
          if (node == tree.root) {
            if (!bot.isAllowedRootMove(loc)) continue;
          }
        }

        considerMove(pos, 0, fpuValue);
      }

#ifdef DEBUG
      if (is_last_playout) {
        sort(vals_debug.begin(), vals_debug.end());
        for (auto& [sv, prob, pos] : vals_debug) {
          const Loc loc =
              NNPos::posToLoc(pos, bot.rootBoard.x_size, bot.rootBoard.y_size,
                              bot.nnXLen, bot.nnYLen);
          const string locString = Location::toString(loc, bot.rootBoard);
          cout << "(" << sv << ", " << prob << ", " << pos << ", " << loc
               << ", " << locString << ")";
        }
        cout << endl;
      }
#endif

      dfs(movePosNode[bestMovePos], dfs);
    };

    helper(tree.root, helper);
    return numNodesAdded;
  };

  for (int i = 0; i < bot.searchParams.maxVisits;) {
#ifdef DEBUG
    cout << endl << "Checking playout #" << i << endl;
    i += checkOnePlayout(i + 1 >= bot.searchParams.maxVisits);
#else
    i += checkOnePlayout();
#endif
  }

  for (auto node : tree.all_nodes) {
    testAssert(visits[node] > 0);
    testAssert(visits[node] == NodeStats(node->stats).visits);
  }
}

Rules AMCTSTests::parseRules(ConfigParser& cfg, Logger& logger) {
  GameInitializer gInit(cfg, logger);
  return gInit.createRules();
}

shared_ptr<NNEvaluator> AMCTSTests::getNNEval(string modelFile,
                                              ConfigParser& cfg, Logger& logger,
                                              uint64_t seed) {
  Setup::initializeSession(cfg);
  Rand seedRand(seed);
  int maxConcurrentEvals = 2;
  int expectedConcurrentEvals = 1;
  int defaultMaxBatchSize = 8;
  bool defaultRequireExactNNLen = false;
  bool disableFP16 = false;
  string expectedSha256 = "";

  NNEvaluator* nnEval = Setup::initializeNNEvaluator(
      modelFile, modelFile, expectedSha256, cfg, logger, seedRand,
      maxConcurrentEvals, expectedConcurrentEvals, NNPos::MAX_BOARD_LEN,
      NNPos::MAX_BOARD_LEN, defaultMaxBatchSize, defaultRequireExactNNLen, disableFP16,
      Setup::SETUP_FOR_OTHER);

  shared_ptr<NNEvaluator> ret(nnEval);
  return ret;
}

shared_ptr<NNResultBuf> AMCTSTests::evaluate(shared_ptr<NNEvaluator> nnEval,
                                             Board& board, BoardHistory& hist,
                                             Player nextPla, bool skipCache,
                                             bool includeOwnerMap) {
  MiscNNInputParams nnInputParams;
  NNResultBuf* buf = new NNResultBuf();
  nnEval->evaluate(board, hist, nextPla, nnInputParams, *buf, skipCache,
                   includeOwnerMap);
  shared_ptr<NNResultBuf> ret(buf);
  return ret;
}

void AMCTSTests::resetBot(Search& bot, int board_size, const Rules& rules) {
  Board board(board_size, board_size);
  BoardHistory hist(board, P_BLACK, rules, 0);
  bot.setPosition(P_BLACK, board, hist);
}

AMCTSTests::SearchTree::SearchTree(const Search& bot)
    : root(bot.rootNode), rootHist(bot.rootHistory) {
  // We don't support graph search yet.
  testAssert(!bot.searchParams.useGraphSearch);

  auto build = [this](const SearchNode* node, auto&& dfs) -> void {
    all_nodes.push_back(node);
    children[node] = {};

    int _;  // Not used
    const auto arr = node->getChildren(_);
    const int numChildren = node->iterateAndCountChildren();
    for (size_t i = 0; i < numChildren; i++) {
      const SearchNode* child = arr[i].getIfAllocated();
      children[node].push_back(child);
      revEdge[child] = {node, arr[i].getMoveLoc()};
      dfs(child, dfs);
    }
  };

  build(root, build);
}

vector<const SearchNode*> AMCTSTests::SearchTree::getSubtreeNodes(
    const SearchNode* subtree_root) const {
  vector<const SearchNode*> subtree_nodes;

  auto walk = [this, &subtree_nodes](const SearchNode* node,
                                     auto&& dfs) -> void {
    subtree_nodes.push_back(node);
    for (auto child : children.at(node)) {
      dfs(child, dfs);
    }
  };

  walk(subtree_root, walk);
  return subtree_nodes;
}

std::vector<const SearchNode*> AMCTSTests::SearchTree::getPathToRoot(
    const SearchNode* node) const {
  vector<const SearchNode*> path = {node};
  while (*path.rbegin() != root) {
    path.push_back(revEdge.at(*path.rbegin()).parent);
  }
  return path;
}

BoardHistory AMCTSTests::SearchTree::getNodeHistory(
    const SearchNode* node) const {
  const auto pathRootToNode = [&]() {
    auto path = getPathToRoot(node);
    std::reverse(path.begin(), path.end());
    return path;
  }();

  Board board = rootHist.getRecentBoard(0);
  BoardHistory hist = rootHist;
  for (auto& n : pathRootToNode) {
    if (n == root) continue;  // Skip root node
    hist.makeBoardMoveTolerant(board, revEdge.at(n).moveLoc,
                               getOpp(n->nextPla));
  }

  return hist;
}

NodeStats AMCTSTests::averageStats(
    const Search& bot, const vector<const SearchNode*>& nodes,
    const unordered_map<const SearchNode*, int>* terminal_node_visits) {
  NodeStats stats;

  // During the following loop, stats will track sums and not averages!
  for (auto node : nodes) {
    const NNOutput* nnOutput = node->getNNOutput();

    if (nnOutput != nullptr) {
      // For a regular node with a nnOutput,
      // we get stats directly from the nnOutput.
      const double winProb = nnOutput->whiteWinProb;
      const double lossProb = nnOutput->whiteLossProb;
      const double noResultProb = nnOutput->whiteNoResultProb;
      const double scoreMean = nnOutput->whiteScoreMean;
      const double scoreMeanSq = nnOutput->whiteScoreMeanSq;
      const double lead = nnOutput->whiteLead;
      const double utility = bot.getUtilityFromNN(*nnOutput);

      const double w = bot.computeWeightFromNode(*node);

      stats.winLossValueAvg += w * (winProb - lossProb);
      stats.noResultValueAvg += w * noResultProb;
      stats.scoreMeanAvg += w * scoreMean;
      stats.scoreMeanSqAvg += w * scoreMeanSq;
      stats.leadAvg += w * lead;
      stats.utilityAvg += w * utility;
      stats.utilitySqAvg += w * utility * utility;

      stats.weightSum += w;
      stats.weightSqSum += w * w;
    } else {
      // If nnOutput is null, this means the node is a terminal node.
      // In this case we need can only get the stats from node->stats.
      const NodeStats termStats(node->stats);
      const double w = (terminal_node_visits == nullptr)
                           ? termStats.weightSum
                           : terminal_node_visits->at(node);

      stats.winLossValueAvg += w * termStats.winLossValueAvg;
      stats.noResultValueAvg += w * termStats.noResultValueAvg;
      stats.scoreMeanAvg += w * termStats.scoreMeanAvg;
      stats.scoreMeanSqAvg += w * termStats.scoreMeanSqAvg;
      stats.leadAvg += w * termStats.leadAvg;
      stats.utilityAvg += w * termStats.utilityAvg;
      stats.utilitySqAvg += w * termStats.utilitySqAvg;

      stats.weightSum += w;
      stats.weightSqSum += termStats.weightSqSum;
    }
  }

  // We fix up the averages at the end.
  stats.winLossValueAvg /= stats.weightSum;
  stats.noResultValueAvg /= stats.weightSum;
  stats.scoreMeanAvg /= stats.weightSum;
  stats.scoreMeanSqAvg /= stats.weightSum;
  stats.leadAvg /= stats.weightSum;
  stats.utilityAvg /= stats.weightSum;
  stats.utilitySqAvg /= stats.weightSum;

  return stats;
}
