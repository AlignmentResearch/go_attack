
#ifndef BOOK_BOOK_H_
#define BOOK_BOOK_H_

#include "../core/global.h"
#include "../core/hash.h"
#include "../core/logger.h"
#include "../game/boardhistory.h"

struct BookHash {
  Hash128 historyHash;
  Hash128 stateHash;

  BookHash();
  BookHash(Hash128 historyHash, Hash128 situationHash);

  bool operator<(const BookHash other) const;
  bool operator>(const BookHash other) const;
  bool operator<=(const BookHash other) const;
  bool operator>=(const BookHash other) const;
  bool operator==(const BookHash other) const;
  bool operator!=(const BookHash other) const;

  BookHash operator^(const BookHash other) const;
  BookHash operator|(const BookHash other) const;
  BookHash operator&(const BookHash other) const;
  BookHash& operator^=(const BookHash other);
  BookHash& operator|=(const BookHash other);
  BookHash& operator&=(const BookHash other);

  // Get book hash, and the symmetry to apply so that hist aligns with book nodes for its current position, (histspace -> nodespace)
  // and the list of symmetries such that book node is invariant under those symmetries.
  static void getHashAndSymmetry(const BoardHistory& hist, int repBound, BookHash& hashRet, int& symmetryToAlignRet, std::vector<int>& symmetriesRet, int bookVersion);

  friend std::ostream& operator<<(std::ostream& out, const BookHash other);
  std::string toString() const;
  static BookHash ofString(const std::string& s);
};

struct BookMove {
  // If you play *move* from this position, you should go to the child node with this hash.
  Loc move;
  // The symmetry you need to apply to a board aligned with this node so that it aligns with the child node. (nodespace -> childnodespace)
  int symmetryToAlign;
  BookHash hash;

  // The policy prior of this move from the neural net.
  double rawPolicy;

  // Computed and filled in dynamically when costs are computed/recomputed.
  double costFromRoot;
  bool isWLPV; // Is this node the best winloss move from its parent?
  double biggestWLCostFromRoot; // Largest single cost due to winloss during path from root

  BookMove();
  BookMove(Loc move, int symmetryToAlign, BookHash hash, double rawPolicy);

  // Apply symmetry to this BookMove.
  BookMove getSymBookMove(int symmetry, int xSize, int ySize);
};

struct BookValues {
  // All values for which the player perspective matters are from white's perspective.
  double winLossValue = 0.0;
  double scoreMean = 0.0;
  double sharpScoreMean = 0.0;

  // Average short term error of nodes in the search. Probably correlated with the confidence
  // of this node, but not necessarily being a meaningful measure of it directly.
  double winLossError = 0.0;
  double scoreError = 0.0;
  // Stdev to the end of the whole game.
  double scoreStdev = 0.0;

  double maxPolicy = 0.0;
  double weight = 0.0;
  double visits = 0.0;

  double getAdjustedWinLossError(const Rules& rules) const;
  double getAdjustedScoreError(const Rules& rules) const;
};
struct RecursiveBookValues {
  // Recursively computed via minimax
  double winLossValue = 0.0;
  double scoreMean = 0.0;
  double sharpScoreMean = 0.0;
  double winLossLCB = 0.0; // minimaxing winLossValue - winLossError * errorFactor
  double scoreLCB = 0.0;   // minimaxing scoreMean - scoreError * errorFactor
  double scoreFinalLCB = 0.0;   // minimaxing scoreMean - scoreStdev * errorFactor
  double winLossUCB = 0.0; // minimaxing winLossValue + winLossError * errorFactor
  double scoreUCB = 0.0;   // minimaxing scoreMean + scoreError * errorFactor
  double scoreFinalUCB = 0.0;   // minimaxing scoreMean + scoreError * errorFactor

  // Weighted by sum
  double weight = 0.0;
  double visits = 0.0;
};

class SymBookNode;
class ConstSymBookNode;
class Book;

class BookNode {
  const BookHash hash;
  Book* const book;  // Non-owning pointer to the book that has this node.
  const Player pla;
  const std::vector<int> symmetries; // List of symmetries under which this position is invariant

  // -----------------------------------------------------------------------------------------------------------
  // Values that the book construction algorithm should set
  // -----------------------------------------------------------------------------------------------------------
  BookValues thisValuesNotInBook;  // Based on a search of this node alone, excluding all current book nodes.
  bool canExpand; // Set to false to never attempt to add more children to this node.
  bool canReExpand; // Set to false to disable reexpansion on this node for this run (not saved for future loads of book).

  // -----------------------------------------------------------------------------------------------------------
  // Values maintained by the book
  // -----------------------------------------------------------------------------------------------------------
  std::map<Loc,BookMove> moves;
  std::vector<std::pair<BookHash,Loc>> parents; // Locations are in the parent's alignment space
  int64_t bestParentIdx; // Lowest cost parent, updated whenever costs are recomputed.

  RecursiveBookValues recursiveValues;  // Based on minimaxing over the book nodes
  int minDepthFromRoot;    // Minimum number of moves to reach this node from root
  double minCostFromRoot;  // Minimum sum of BookMove cost to reach this node from root
  double thisNodeExpansionCost;  // The cost for picking this node to expand further.
  double minCostFromRootWLPV;  // minCostFromRoot of the cheapest node that this node is the winLoss pv of.
  bool expansionIsWLPV; // True if the winloss PV for this node is to expand it, rather than an existing child.
  double biggestWLCostFromRoot; // Largest single cost due to winloss during path from root

  BookNode(BookHash hash, Book* book, Player pla, const std::vector<int>& symmetries);
  ~BookNode();
  BookNode(const BookNode&) = delete;
  BookNode& operator=(const BookNode&) = delete;
  BookNode(BookNode&& other) = delete;
  BookNode& operator=(BookNode&& other) = delete;

  friend class ConstSymBookNode;
  friend class SymBookNode;
  friend class Book;
};

class SymBookNode {
  BookNode* node;
  int symmetryOfNode;  // The symmetry applied to node to get this SymBookNode. (nodespace -> symbooknodespace)
  int invSymmetryOfNode;  // The symmetry to apply to SymBookNode locs to convert them to node locs. (symbooknodespace -> nodespace)

  SymBookNode(std::nullptr_t);
  SymBookNode(BookNode* node, int symmetry);

 public:
  SymBookNode();
  SymBookNode(const SymBookNode& other) = default;
  SymBookNode& operator=(const SymBookNode& other) = default;

  bool isNull();
  SymBookNode applySymmetry(int symmetry);

  bool isMoveInBook(Loc move);
  int numUniqueMovesInBook();
  std::vector<BookMove> getUniqueMovesInBook();

  Player pla();
  BookHash hash();
  std::vector<int> getSymmetries();

  BookValues& thisValuesNotInBook();
  bool& canExpand();
  bool& canReExpand();
  const RecursiveBookValues& recursiveValues();
  int minDepthFromRoot();
  double minCostFromRoot();
  double totalExpansionCost();

  // Returns NULL for the root or if somehow a parent is not found
  SymBookNode canonicalParent();

  SymBookNode follow(Loc move);

  // Returns NULL if the move is not legal OR the move is not in the book.
  SymBookNode playMove(Board& board, BoardHistory& hist, Loc move);
  // Returns NULL if the move is not legal. The move *must* not be in the book.
  SymBookNode playAndAddMove(Board& board, BoardHistory& hist, Loc move, double rawPolicy, bool& childIsTransposing);

  // Returns false and does not modify ret if playing the moves in the book to reach here hit an illegal move.
  // Fills moveHistoryRet with the sequence of moves played. If there is an illegal move, includes the illegal move.
  // This should only happen if a book was loaded from disk that is corrupted, or else only astronomically rarely on hash collisions.
  bool getBoardHistoryReachingHere(BoardHistory& ret, std::vector<Loc>& moveHistoryRet);

  friend class ConstSymBookNode;
  friend class Book;
};

class ConstSymBookNode {
  const BookNode* node;
  int symmetryOfNode;  // The symmetry applied to node to get this ConstSymBookNode. (nodespace -> symbooknodespace)
  int invSymmetryOfNode;  // The symmetry to apply to ConstSymBookNode locs to convert them to node locs. (symbooknodespace -> nodespace)

  ConstSymBookNode(std::nullptr_t);
  ConstSymBookNode(const BookNode* node, int symmetry);

 public:
  ConstSymBookNode();
  ConstSymBookNode(const SymBookNode& other);
  ConstSymBookNode(const ConstSymBookNode& other) = default;
  ConstSymBookNode& operator=(const SymBookNode& other);
  ConstSymBookNode& operator=(const ConstSymBookNode& other) = default;

  bool isNull();
  ConstSymBookNode applySymmetry(int symmetry);

  Player pla();
  BookHash hash();
  std::vector<int> getSymmetries();

  bool isMoveInBook(Loc move);
  int numUniqueMovesInBook();
  std::vector<BookMove> getUniqueMovesInBook();

  const BookValues& thisValuesNotInBook();
  bool canExpand();
  bool canReExpand();
  const RecursiveBookValues& recursiveValues();
  int minDepthFromRoot();
  double minCostFromRoot();
  double totalExpansionCost();

  // Returns NULL for the root or if somehow a parent is not found
  ConstSymBookNode canonicalParent();

  ConstSymBookNode follow(Loc move);
  // Returns NULL if the move is not legal OR the move is not in the book.
  ConstSymBookNode playMove(Board& board, BoardHistory& hist, Loc move);

  // Returns false and does not modify ret if playing the moves in the book to reach here hit an illegal move.
  // This should only happen if a book was loaded from disk that is corrupted, or else only astronomically rarely on hash collisions.
  bool getBoardHistoryReachingHere(BoardHistory& ret, std::vector<Loc>& moveHistoryRet);

  friend class Book;
};

// Book object for storing and minimaxing stats based on deep search, supports full tranposing symmetry handling.
// In the case where initialBoard is non-square, transpose symmetries are disallowed everywhere, so
// every node in the book always agrees on these. The tradeoff is that books don't work for
// rectangular boards in the wrong orientation, it's up to the user to manually do that.
class Book {
  static constexpr size_t NUM_HASH_BUCKETS = 2048;
  static const std::string BOOK_JS1;
  static const std::string BOOK_JS2;
  static const std::string BOOK_JS3;
  static const std::string BOOK_CSS;

 public:
  const int bookVersion;
  const Board initialBoard;
  const Rules initialRules;
  const Player initialPla;
  const int repBound;

 private:
  // This times shortterm error is considered the stdev for UCB purposes.
  double errorFactor;
  // Fixed cost per move
  double costPerMove;
  // Cost per 1 unit of winloss value that a move's UCB is worse than the best UCB
  // As well as versions that compare winloss^3 and winloss^7, to emphasize the tails.
  double costPerUCBWinLossLoss;
  double costPerUCBWinLossLossPow3;
  double costPerUCBWinLossLossPow7;
  // Cost per point of score that a move's UCB is better than the best UCB
  double costPerUCBScoreLoss;
  // Cost per nat of log policy that a move is less likely than 100%.
  double costPerLogPolicy;
  // For expanding new moves - extra penalty per move or move squared already expanded at a node.
  double costPerMovesExpanded;
  double costPerSquaredMovesExpanded;
  // Cost when pass is the favorite move (helps truncate lines that are solved to the end of game)
  double costWhenPassFavored;
  // Bonuses per difference between UCB and LCB
  double bonusPerWinLossError;
  double bonusPerScoreError;
  // Bonus per point of score difference between sharp score and plain lead
  double bonusPerSharpScoreDiscrepancy;
  // Bonus per policy mass that is not expanded at a node, encourage expanding most of the policy mass.
  double bonusPerExcessUnexpandedPolicy;
  // Bonus per winloss by which the unexpanded node is better than any of the moves that have been explored.
  double bonusPerUnexpandedBestWinLoss;
  // Bonus if a move is the PV in terms of winloss, if that winloss value is near 0, as a cost reduction factor.
  double bonusForWLPV1;
  // Bonus if a move is the PV in terms of winloss, if that winloss value is near -0.5 or +0.5, as a cost reduction factor.
  double bonusForWLPV2;
  // Bonus for the biggest single WL cost on a given path, per unit of cost. (helps favor lines with only 1 mistake but not lines with more than one)
  double bonusForBiggestWLCost;
  // Cap on how bad UCBScoreLoss can be.
  double scoreLossCap;
  // Reduce costs near the start of a book. First move costs are reduced by earlyBookCostReductionFactor
  // and this gets multiplied by by earlyBookCostReductionLambda per move deeper.
  double earlyBookCostReductionFactor;
  double earlyBookCostReductionLambda;
  // Affects html rendering - used for integrating score into sorting of moves.
  double utilityPerScore;
  double policyBoostSoftUtilityScale;
  double utilityPerPolicyForSorting;
  // Allow re-expanding a node if it has <= this many visits
  double maxVisitsForReExpansion;
  // How many visits such that below this many is considered not many? Used to scale some visit-based cost heuristics.
  double visitsScale;
  // When rendering - cap sharp scores that differ by more than this many points from regular score.
  double sharpScoreOutlierCap;
  std::map<BookHash,double> bonusByHash;
  std::map<BookHash,double> expandBonusByHash;
  std::map<BookHash,double> visitsRequiredByHash;
  std::map<BookHash,int> branchRequiredByHash;

  int initialSymmetry; // The symmetry that needs to be applied to initialBoard to align it with rootNode. (initialspace -> rootnodespace)
  BookNode* root;
  std::vector<BookNode*> nodes;
  std::map<BookHash,int64_t>* nodeIdxMapsByHash;
 public:
  Book(
    int bookVersion,
    const Board& board,
    Rules rules,
    Player initialPla,
    int repBound,
    double errorFactor,
    double costPerMove,
    double costPerUCBWinLossLoss,
    double costPerUCBWinLossLossPow3,
    double costPerUCBWinLossLossPow7,
    double costPerUCBScoreLoss,
    double costPerLogPolicy,
    double costPerMovesExpanded,
    double costPerSquaredMovesExpanded,
    double costWhenPassFavored,
    double bonusPerWinLossError,
    double bonusPerScoreError,
    double bonusPerSharpScoreDiscrepancy,
    double bonusPerExcessUnexpandedPolicy,
    double bonusPerUnexpandedBestWinLoss,
    double bonusForWLPV1,
    double bonusForWLPV2,
    double bonusForBiggestWLCost,
    double scoreLossCap,
    double earlyBookCostReductionFactor,
    double earlyBookCostReductionLambda,
    double utilityPerScore,
    double policyBoostSoftUtilityScale,
    double utilityPerPolicyForSorting,
    double maxVisitsForReExpansion,
    double visitsScale,
    double sharpScoreOutlierCap
  );
  ~Book();

  static constexpr int LATEST_BOOK_VERSION = 2;

  Book(const Book&) = delete;
  Book& operator=(const Book&) = delete;
  Book(Book&& other) = delete;
  Book& operator=(Book&& other) = delete;

  BoardHistory getInitialHist() const;
  // Get the initial history, with symmetry applied
  BoardHistory getInitialHist(int symmetry) const;

  size_t size() const;

  double getErrorFactor() const;
  void setErrorFactor(double d);
  double getCostPerMove() const;
  void setCostPerMove(double d);
  double getCostPerUCBWinLossLoss() const;
  void setCostPerUCBWinLossLoss(double d);
  double getCostPerUCBWinLossLossPow3() const;
  void setCostPerUCBWinLossLossPow3(double d);
  double getCostPerUCBWinLossLossPow7() const;
  void setCostPerUCBWinLossLossPow7(double d);
  double getCostPerUCBScoreLoss() const;
  void setCostPerUCBScoreLoss(double d);
  double getCostPerLogPolicy() const;
  void setCostPerLogPolicy(double d);
  double getCostPerMovesExpanded() const;
  void setCostPerMovesExpanded(double d);
  double getCostPerSquaredMovesExpanded() const;
  void setCostPerSquaredMovesExpanded(double d);
  double getCostWhenPassFavored() const;
  void setCostWhenPassFavored(double d);
  double getBonusPerWinLossError() const;
  void setBonusPerWinLossError(double d);
  double getBonusPerScoreError() const;
  void setBonusPerScoreError(double d);
  double getBonusPerSharpScoreDiscrepancy() const;
  void setBonusPerSharpScoreDiscrepancy(double d);
  double getBonusPerExcessUnexpandedPolicy() const;
  void setBonusPerExcessUnexpandedPolicy(double d);
  double getBonusPerUnexpandedBestWinLoss() const;
  void setBonusPerUnexpandedBestWinLoss(double d);
  double getBonusForWLPV1() const;
  void setBonusForWLPV1(double d);
  double getBonusForWLPV2() const;
  void setBonusForWLPV2(double d);
  double getBonusForBiggestWLCost() const;
  void setBonusForBiggestWLCost(double d);
  double getScoreLossCap() const;
  void setScoreLossCap(double d);
  double getEarlyBookCostReductionFactor() const;
  void setEarlyBookCostReductionFactor(double d);
  double getEarlyBookCostReductionLambda() const;
  void setEarlyBookCostReductionLambda(double d);
  double getUtilityPerScore() const;
  void setUtilityPerScore(double d);
  double getPolicyBoostSoftUtilityScale() const;
  void setPolicyBoostSoftUtilityScale(double d);
  double getUtilityPerPolicyForSorting() const;
  void setUtilityPerPolicyForSorting(double d);
  double getMaxVisitsForReExpansion() const;
  void setMaxVisitsForReExpansion(double d);
  double getVisitsScale() const;
  void setVisitsScale(double d);

  std::map<BookHash,double> getBonusByHash() const;
  void setBonusByHash(const std::map<BookHash,double>& d);
  std::map<BookHash,double> getExpandBonusByHash() const;
  void setExpandBonusByHash(const std::map<BookHash,double>& d);
  std::map<BookHash,double> getVisitsRequiredByHash() const;
  void setVisitsRequiredByHash(const std::map<BookHash,double>& d);
  std::map<BookHash,int> getBranchRequiredByHash() const;
  void setBranchRequiredByHash(const std::map<BookHash,int>& d);

  // Gets the root node, in the orientation of the initial board.
  SymBookNode getRoot();
  ConstSymBookNode getRoot() const;

  // Walk down the book following hist and get the final node.
  // Returns a null SymBookNode if hist goes off the end of the book.
  SymBookNode get(const BoardHistory& hist);
  ConstSymBookNode get(const BoardHistory& hist) const;
  SymBookNode getByHash(BookHash hash);
  ConstSymBookNode getByHash(BookHash hash) const;

  void recompute(const std::vector<SymBookNode>& newAndChangedNodes);
  void recomputeEverything();

  std::vector<SymBookNode> getNextNToExpand(int n);
  std::vector<SymBookNode> getAllLeaves(double minVisits);
  std::vector<SymBookNode> getAllNodes();

  // Return the number of files written
  int64_t exportToHtmlDir(
    const std::string& dirName,
    const std::string& rulesLabel,
    const std::string& rulesLink,
    bool devMode,
    double htmlMinVisits,
    Logger& logger
  );

  void saveToFile(const std::string& fileName) const;
  static Book* loadFromFile(const std::string& fileName, double sharpScoreOutlierCap);

 private:
  int64_t getIdx(BookHash hash) const;
  BookNode* get(BookHash hash);
  const BookNode* get(BookHash hash) const;
  bool add(BookHash hash, BookNode* node);

  enum class DFSAction {
    recurse, // Recursively search this node
    skip,    // Don't recurse into this node but keep searching
    abort    // Abort the entire search
  };

  bool reverseDepthFirstSearchWithMoves(
    const BookNode* initialNode,
    bool preferLowCostParents,
    const std::function<DFSAction(const std::vector<const BookNode*>&, const std::vector<Loc>&)>& f
  ) const;

  bool reverseDepthFirstSearchWithPostF(
    BookNode* initialNode,
    const std::function<DFSAction(BookNode*)>& f,
    const std::function<void(BookNode*)>& postF
  );

  void iterateDirtyNodesPostOrder(
    const std::set<BookHash>& dirtyNodes,
    bool allDirty,
    const std::function<void(BookNode* node)>& f
  );

  void iterateEntireBookPreOrder(
    const std::function<void(BookNode*)>& f
  );

  void recomputeNodeValues(BookNode* node);
  void recomputeNodeCost(BookNode* node);

  double getUtility(const RecursiveBookValues& values) const;

  friend class BookNode;
  friend class SymBookNode;
  friend class ConstSymBookNode;
};


#endif // BOOK_BOOK_H_
