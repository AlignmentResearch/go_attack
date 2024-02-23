import argparse
import itertools
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from go_attack.go import Color, Game

BOARD_LEN = 19
CAPTURE_GROUP_SIZE_THRESHOLD = 20

# Substrings that appear uniquely in adversaries' and victims' names and are
# used to identify which player is the adversary.
ADVERSARY_NAME_SUBSTRINGS = ["adv"]
VICTIM_NAME_SUBSTRINGS = ["victim", "b18-"]


def get_sgf_property(property_name: str, sgf_string: str) -> str:
    return re.search(f"{property_name}\[([^\]]+)\]", sgf_string).group(1)


def get_cycle_interior(cyclic_group: np.ndarray) -> (np.ndarray, (int, int)):
    """Returns boolean map of points inside cyclic group.

    Args
    ----
    cyclic_group:
      Boolean map of cyclic group points.
    """

    visited = np.zeros_like(cyclic_group, dtype=bool)
    interior = ~cyclic_group
    adjacencies = [[0, -1], [0, 1], [-1, 0], [1, 0]]
    x_max, y_max = cyclic_group.shape

    def dfs(x, y, definitely_not_interior=False):
        visited[x, y] = True

        if (
            definitely_not_interior
            or x == 0
            or y == 0
            or x == x_max - 1
            or y == y_max - 1
        ):
            interior[x, y] = False
            definitely_not_interior = True

        for x_inc, y_inc in adjacencies:
            x_new = x + x_inc
            y_new = y + y_inc
            if (
                not (0 <= x_new < x_max)
                or not (0 <= y_new < y_max)
                or cyclic_group[x_new, y_new]
            ):
                continue
            if not visited[x_new, y_new]:
                dfs(x_new, y_new, definitely_not_interior=definitely_not_interior)
            if not interior[x_new, y_new]:
                interior[x, y] = False

    for x, y in np.ndindex(cyclic_group.shape):
        if not visited[x, y] and not cyclic_group[x, y]:
            dfs(x, y)

    return interior


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", type=Path, nargs="+")
    parser.add_argument("--title", type=str, default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cycle_heatmap = np.zeros((BOARD_LEN, BOARD_LEN))
    adversary_heatmap = np.zeros((BOARD_LEN, BOARD_LEN))
    victim_heatmap = np.zeros((BOARD_LEN, BOARD_LEN))
    interior_adversary_heatmap = np.zeros((BOARD_LEN, BOARD_LEN))
    interior_victim_heatmap = np.zeros((BOARD_LEN, BOARD_LEN))
    num_cycles = 0
    for path in args.files:
        if ".sgf" in path.suffix:
            sgf_files = [path]
        else:
            sgf_files = itertools.chain(path.glob("**/*.sgf"), path.glob("**/*.sgfs"))

        for sgf_file in sgf_files:
            for sgf_string in open(sgf_file):

                # Filter for games with the correct board size and with the
                # adversary winning.
                if int(get_sgf_property("SZ", sgf_string)) != BOARD_LEN:
                    continue
                b_name = get_sgf_property("PB", sgf_string)
                w_name = get_sgf_property("PW", sgf_string)
                winner = get_sgf_property("RE", sgf_string)[0]
                adversary_is_w = False
                adversary_is_b = False
                for name in ADVERSARY_NAME_SUBSTRINGS:
                    if name in b_name:
                        adversary_is_b = True
                    if name in w_name:
                        adversary_is_w = True
                for name in VICTIM_NAME_SUBSTRINGS:
                    if name in b_name:
                        adversary_is_w = True
                    if name in w_name:
                        adversary_is_b = True
                assert (
                    adversary_is_w != adversary_is_b
                ), f"Couldn't determine adversary: {b_name} vs. {w_name}"
                adversary_win = (adversary_is_b and winner == "B") or (
                    adversary_is_w and winner == "W"
                )
                if not adversary_win:
                    continue
                adversary_color = Color.BLACK if adversary_is_b else Color.WHITE

                game = Game.from_sgf(sgf_string)

                for i, (prev_board, board) in enumerate(
                    zip(game.board_states, game.board_states[1:])
                ):
                    player_color = Color.BLACK if i % 2 == 0 else Color.WHITE
                    if player_color != adversary_color:
                        continue
                    # Check for captures by diffing the previous board with the
                    # current board.
                    opponent_color = player_color.opponent()
                    opponent_stones = prev_board == opponent_color.value
                    empty_points = board == Color.EMPTY.value
                    captured_stones = empty_points & opponent_stones

                    # When the adversary captures lots of victim stones and the
                    # victim stones enclose at least one empty or adversary
                    # square, we guess that it's capturing a cyclic group.
                    if np.count_nonzero(captured_stones) >= CAPTURE_GROUP_SIZE_THRESHOLD:
                        interior = get_cycle_interior(captured_stones)
                        interior_points = interior.nonzero()
                        if len(interior_points[0]) == 0:
                            continue

                        num_cycles += 1

                        # To get rid of some symmetries, flip cyclic group so
                        # that it's in the top-left corner.
                        # (There are still two symmetries that this doesn't
                        # distinguish since you can flip the board diagonally
                        # and keep the cyclic group in the top-left. This also
                        # doesn't get rid of symmetries if the cyclic group is
                        # in the center of the board.)
                        interior_centroid = np.average(interior.nonzero(), axis=1)
                        for axis, coord in enumerate(interior_centroid):
                            if coord > BOARD_LEN / 2:
                                board = np.flip(board, axis)
                                captured_stones = np.flip(captured_stones, axis)
                                interior = np.flip(interior, axis)

                        adversary_stones = board == player_color.value
                        victim_stones = board == opponent_color.value
                        interior_adversary_stones = interior & adversary_stones
                        interior_victim_stones = interior & victim_stones

                        cycle_heatmap += captured_stones
                        adversary_heatmap += adversary_stones
                        victim_heatmap += victim_stones
                        interior_adversary_heatmap += interior_adversary_stones
                        interior_victim_heatmap += interior_victim_stones

                        break

    fig, axs = plt.subplots(3, 2)

    def plot_data(figure_row, figure_column, data, title):
        ax = axs[figure_row, figure_column]
        im = ax.imshow(data / num_cycles, cmap="hot", interpolation="nearest", vmax=1.0)
        ax.title.set_text(title)
        return im

    plot_data(0, 0, cycle_heatmap, "Cyclic group")
    axs[0, 1].axis("off")
    plot_data(1, 0, adversary_heatmap, "Adversary stones")
    plot_data(1, 1, interior_adversary_heatmap, "Interior adversary stones")
    plot_data(2, 0, victim_heatmap, "Victim stones")
    im = plot_data(2, 1, interior_victim_heatmap, "Interior victim stones")
    for _, ax in np.ndenumerate(axs):
        ax.set_xticks(range(0, board.shape[0], 5))
        ax.set_yticks(range(0, board.shape[1], 5))
        ax.set_xticks(range(board.shape[0]), minor=True)
        ax.set_yticks(range(board.shape[1]), minor=True)
        ax.xaxis.set_ticks_position("both")
        ax.yaxis.set_ticks_position("both")
    fig.suptitle(f"{args.title}, sample size of {num_cycles}")
    fig.tight_layout()
    fig.colorbar(im, ax=axs.ravel().tolist(), location="left")

    if args.output is None:
        plt.show()
    else:
        fig.savefig(args.output)


if __name__ == "__main__":
    main()
