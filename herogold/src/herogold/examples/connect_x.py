import copy
import math
import random
from collections.abc import Generator
from functools import cache
from typing import Optional

type BoardType = list[list[str]]
type Coordinate = tuple[int, int]
type Coordinates = list[Coordinate]
type CoordsGenerator = Generator[Coordinates, None, None]
MAX_BOARD_SIZE_PRINT = 50


class Board:
    SPACE = " "
    NO_END = ""
    DRAW = "Draw"
    x = "X"
    o = "O"
    board_state: BoardType
    winning_coords: Coordinates
    width: int
    height: int
    victory_target: int


    def __init__(
        self,
        width: int=7,
        height: int=5,
        victory_target: int=4,
    ) -> None:
        self.width = width
        self.height = height
        self.victory_target = victory_target
        self.empty_board()


    def empty_board(self) -> None:
        if not self.board_state:
            self._new_board()
        else:
            self._clear_board()


    def _new_board(self) -> None:
        self.board_state = []
        for row in range(self.height):
            self.board_state.append([])
            for column in range(self.width):
                self.board_state[row].append([])
                self.board_state[row][column] = self.SPACE


    def _clear_board(self) -> None:
        del self.board_state
        self._new_board()


    def is_fully_filled(self) -> bool:
        for row in range(self.height):
            for column in range(self.width):
                if self.board_state[row][column] == self.SPACE:
                    return False
        return True


    def _make_random_moves(self, count: int = 0, inverse: bool = False) -> None:
        if self.is_fully_filled():
            return
        for i in range(count):
            target = (self.o if i % 2 else self.x) if inverse else self.x if i % 2 else self.o
            try:
                self.add_move(random.randint(0, self.width - 1), target)
            except ValueError:
                # if current player is X (default) then next player should be O
                inverted = target == self.x

                self._make_random_moves(1, inverted)


    def _fill_board(self) -> None:
        """Fills the board completely with random moves."""
        self._make_random_moves(self.width * self.height)


    def add_move(self, column: int, xo: str) -> None:
        self.validate_move(column, xo)

        # Fill from bottom up
        for row in range(self.height - 1, -1, -1):
            if self.board_state[row][column] != self.SPACE:
                continue  # ignore already filled rows
            self.board_state[row][column] = xo
            return  # Stop when empty spot is set to XO


    def _remove_move(self, column: int) -> None:
        """Remove a move from a column, removes the FIRST non empty space in a given column.

        Parameters
        ----------
        :param:`column`: :class:`int`
            The column to remove a piece from

        """
        for row in range(self.height):
            if self.board_state[row][column] != self.SPACE:
                self.board_state[row][column] = self.SPACE
                return


    def validate_move(self, column: int, xo: str) -> None:
        if (
            column >= self.width
            or column < 0
        ):
            msg = f"Column not in range of 0-{self.width}"
            raise ValueError(msg)
        if xo not in [self.x, self.o]:
            msg = f"Expected X or O but got {xo}"
            raise ValueError(msg)
        if self.is_column_filled(column):
            msg = f"Given column {column} is already full!"
            raise ValueError(msg)


    def is_column_filled(self, column: int) -> bool:
        for row in range(self.height):
            if self.board_state[row][column] == self.SPACE:
                return False
        return True


    def print_board(self) -> None:
        for row in range(self.height):
            for column in range(self.width):
                self.board_state[row][column]
        for _ in range(self.width * 2):
            pass

        for row in range(self.width):
            pass


    def print_winning_board(self) -> None:
        """Same as print_board but with colors highlighting the wining line!"""
        winner = self.get_winner()
        if winner is None:
            self.print_board()
            return

        if winner == self.DRAW:
            self.print_board()
            return

        for row in range(self.height):
            for column in range(self.width):
                self.board_state[row][column]
                if (row, column) in self.winning_coords:
                    pass
                else:
                    pass
        for _ in range(self.width * 2):
            pass

        for row in range(self.width):
            pass


    def check_winner(self, xo_to_check: str):
        return any([
            self._check_horizontal_winner(xo_to_check),
            self._check_vertical_winner(xo_to_check),
            self._check_diagonal_winner(xo_to_check),
        ])


    def get_winner(self):
        if self.check_winner(self.x):
            return self.x
        if self.check_winner(self.o):
            return self.o
        if self.is_fully_filled():
            self.winning_coords = None
            return self.DRAW
        return None


    def _check_vertical_winner(self, xo_to_check: str = "") -> bool:
        if not xo_to_check:
            return self._check_vertical_winner(xo_to_check=self.x) or self._check_vertical_winner(xo_to_check=self.o)

        total_in_line = 0

        for column in range(self.width):
            total_in_line = 0  # reset counter when checking next vertical win
            winning_line: Coordinates = []
            for row in range(self.height):
                if total_in_line >= self.victory_target:
                    self.winning_coords = winning_line
                    return True
                if self.board_state[row][column] == xo_to_check:
                    total_in_line += 1
                    winning_line.append((row, column))
                    continue
                total_in_line = 0
                winning_line = []
        return False


    def _check_horizontal_winner(self, xo_to_check: str = "") -> bool:
        if not xo_to_check:
            return self._check_horizontal_winner(xo_to_check=self.x) or self._check_horizontal_winner(xo_to_check=self.o)

        total_in_line = 0

        for row in range(self.height):
            total_in_line = 0  # reset counter when checking next horizontal win
            winning_line: Coordinates = []
            for column in range(self.width):
                if total_in_line >= self.victory_target:
                    self.winning_coords = winning_line
                    return True
                if self.board_state[row][column] == xo_to_check:
                    total_in_line += 1
                    winning_line.append((row, column))
                    continue
                total_in_line = 0
                winning_line = []
        return False


    @staticmethod
    def _fix_diagonal_row_offset(result: CoordsGenerator, offset: int) -> CoordsGenerator:
        """Fixes the row offset when the board was passed into get_diagonals."""
        for li in result:
            diagonal: Coordinates = []
            for tup in li:
                # create new tuple with +1 to the affected coordinate
                # to reflect the board differences
                diagonal.append((tup[0] + offset, tup[1]))
                """same as:
                t1, t2 = tup
                t1 += 1
                t2 += 1
                diag.append(t1, t2)
                """
            yield diagonal


    @staticmethod
    def _fix_diagonal_column_offset(result: CoordsGenerator, offset: int) -> CoordsGenerator:
        """Fixes the column offset when the board was passed into get_diagonals."""
        for li in result:
            diagonal: Coordinates = []
            for tup in li:
                # See _fix_diagonal_row_offset for explanation
                diagonal.append((tup[0], tup[1] + offset))
            yield diagonal


    def get_rows(self, board: Optional[BoardType]=None):
        if board is None:
            board = self.board_state

        for i, row in enumerate(board):
            yield row, i


    def get_columns(self, board: Optional[BoardType]=None):
        if board is None:
            board = self.board_state

        columns: dict[int, str] = {}
        for row in board:
            for i, column in enumerate(row):
                try:
                    columns[i] += column
                except KeyError:
                    columns[i] = column

        # Convert to list, to match get_rows and get_diagonals
        for i, s in columns.items():
            columns[i] = list(s)
        columns: dict[int, list[str]]

        for i in columns:
            yield columns[i], i


    def get_diagonals(self, board: BoardType=None):
        for coords in self.get_diagonal_coords(board):
            diagonal: list[str] = []
            for coord in coords:
                row, column = coord
                diagonal.append(self.board_state[row][column])
            yield diagonal


    def get_diagonal_coords(self, board: BoardType=None, offset: int=0) -> CoordsGenerator:
        """Gets all possible diagonals on this board.

        Yields
        ------
        list of coordinates that makes up a single diagonal

        """
        if not board:
            board = self.board_state
        row_count = len(board)
        column_count = len(board[0])

        if row_count >= self.victory_target and column_count >= self.victory_target:
            offset += 1
            result = self.get_diagonal_coords(board[1:], offset)  # Use a board with one less top row
            result_2 = self.get_diagonal_coords(board[:1], offset)  # Use a board with one less bottom row
            yield from self._fix_diagonal_row_offset(result, 1)
            yield from self._fix_diagonal_row_offset(result_2, 0)

            board_2 = [row[1:] for row in board]  # Create new board, with one less left column
            board_3 = [row[:1] for row in board]  # Create new board, with one less right column
            result = self.get_diagonal_coords(board_2, offset)
            result_2 = self.get_diagonal_coords(board_3, offset)
            yield from self._fix_diagonal_column_offset(result, 1)
            yield from self._fix_diagonal_column_offset(result_2, 0)

        if row_count == column_count:
            # Top left to bottom right: \
            coords: Coordinates = []
            for i in range(row_count):
                coords.append((i, i))
            yield coords

            # Bottom left to top right: /
            coords: Coordinates = []
            for i in range(row_count):
                coords.append((i, row_count - i - 1))
            yield coords


    def is_on_edge(self, coord: Coordinate) -> bool:
        row, column = coord
        if row in range(self.height) and (column == 0 or column == self.width -1):
            return True
        return bool(column in range(self.width) and (row == 0 or row == self.height - 1))


    def match_coordinate(self, coordinate: Coordinate, xo_to_check: str) -> bool:
        return self.board_state[coordinate[0]][coordinate[1]] == xo_to_check


    def _find_diagonal_winner(self, xo_to_check: str="", coordinate: Coordinate=None, previous_coord: Coordinate=None):
        row = coordinate[0]
        column = coordinate[1]

        # Outside the board
        if not (
            0 <= row < self.height
            and 0 <= column < self.width
        ):
            return 0

        top_left = row - 1, column - 1
        bottom_left = row + 1, column - 1
        top_right = row - 1, column + 1
        bottom_right = row + 1, column + 1

        # print clockwise
        # print(top_left, top_right, coordinate, bottom_left, bottom_right)

        score = 0

        if self.is_on_edge(coordinate) and previous_coord:
            if self.match_coordinate(coordinate, xo_to_check):
                self.winning_coords.append(coordinate)
                return 1
            return 0

        # Find direction and keep going that way
        if previous_coord == top_left:
            # \\ Down
            score += self._find_diagonal_winner(xo_to_check, bottom_right, coordinate)

        elif previous_coord == top_right:
            # / Down
            score += self._find_diagonal_winner(xo_to_check, bottom_left, coordinate)

        elif previous_coord == bottom_left:
            # / Up
            score += self._find_diagonal_winner(xo_to_check, top_right, coordinate)

        elif previous_coord == bottom_right:
            # \\ Up
            score += self._find_diagonal_winner(xo_to_check, top_left, coordinate)

        if self.match_coordinate(coordinate, xo_to_check):
            score += 1
            self.winning_coords.append(coordinate)
        else:
            # Reset score and tracked coordinates if we find mismatch
            score = 0
            self.winning_coords = []

        # No need to branch off if random directions,
        # return before for loop to avoid branching infinitely
        if previous_coord:
            return score

        start_score = score
        for coord in [top_left, top_right, bottom_left, bottom_right]:
            score += self._find_diagonal_winner(xo_to_check, coord, coordinate)
            if score >= self.victory_target:
                return xo_to_check
            # reset score when changing directions
            score = start_score
        return None


    def _check_diagonal_winner(self, xo_to_check: str="", starting_coord: Coordinate=None) -> bool:
        if not starting_coord:
            for row in range(self.height):
                for column in range(self.width):
                    winner = self._check_diagonal_winner(xo_to_check, starting_coord=(row,column))
                    if winner:
                        return True
            return False

        # Set winning coords to empty list, preparation for tracking coords
        self.winning_coords = []
        return bool(isinstance(self._find_diagonal_winner(xo_to_check, starting_coord), str))


    def get_diagonal_winner(self, xo_to_check: str=""):
        if xo_to_check:
            return self._check_diagonal_winner(xo_to_check)

        for i in [self.x, self.o]:
            if self._check_diagonal_winner(i):
                return i
        return None


    @property
    def board_size(self):
        return self.height * self.width


    def play_full_random_game(self) -> None:
        i = 0
        while not self.is_fully_filled(): # (winner := self.get_winner()) is None
            i += 1
            if self.board_size < MAX_BOARD_SIZE_PRINT:
                self.print_board()
            self._make_random_moves(1)
            self._make_random_moves(1, True)

        self.print_board()
        self.print_winning_board()
        self.get_winner()


    def get_playable_columns(self):
        for _, idx in self.get_columns():
            if not self.is_column_filled(idx):
                yield idx


class MiniMax:
    DRAW = 0

    def __init__(self, board: Board) -> None:
        self.board = board

    @cache
    def minimax(
        self,
        board: Optional[Board]=None,
        depth: int=-1,
        alpha: int=-math.inf,
        beta: int=math.inf,
        maximizing_player: bool=True,
    ) -> tuple[float, int]:
        """Uses the minimax algorithm to get the best column to place a piece.

        Parameters
        ----------
        :param:`board`: :class:`Optional[Board]`, optional
            The Board, by default self.Board
        :param:`depth`: :class:`int`, optional
            Depth of the algorithm, set to -1 to go infinite, by default 10
        :param:`alpha`: :class:`int`, optional
            Alpha value, used internally, don't give a value, by default -math.inf
        :param:`beta`: :class:`int`, optional
            Beta value, used internally, don't give a value, by default math.inf
        :param:`maximizing_player`: :class:`bool`, optional
            Check for maximizing player or not, don't give a value, by default True

        Returns
        -------
        :class:`tuple[float, int]`
            Score and location of the selected column

        """
        # X = maximizing_player
        if board is None:
            board = self.board

        if depth == 0:
            return 0, 0

        winner = board.get_winner()
        filled = board.is_fully_filled()
        if winner or filled:
            if winner == board.x:
                return 1*10000, 0
            if winner == board.o:
                return -1*10000, 0
            return self.DRAW, 0

        b = copy.deepcopy(board)
        valid_moves = list(b.get_playable_columns())

        if maximizing_player:
            score = -math.inf
            column = random.choice(valid_moves)

            for move in valid_moves:
                if b.is_column_filled(move):
                    continue
                b.add_move(move, Board.x)

                o_score, _ = self.minimax(b, depth-1, alpha, beta, not maximizing_player)

                if o_score > score:
                    score = o_score
                    column = move

                # update alpha to be the new best if we have it
                alpha = max(score, alpha)

                if alpha >= beta:
                    break
                if board.is_fully_filled():
                    break
            return score, column
        # Same as above, except alpha is beta, and we minimize as player o
        score = math.inf
        column = random.choice(valid_moves)

        for move in valid_moves:
            if b.is_column_filled(move):
                continue
            b.add_move(move, Board.o)

            o_score, _ = self.minimax(b, depth-1, alpha, beta, not maximizing_player)

            if o_score < score:
                score = o_score
                column = move

            # update beta to be the new best if we have it
            beta = min(score, beta)

            if alpha >= beta:
                break
            if board.is_fully_filled():
                break
        return score, column


def test_board() -> None:
    b = Board(width=30, height=10, victory_target=6)
    diag_win = None
    while not diag_win:
        b.empty_board()
        b.play_full_random_game()
        diag_win = b.get_diagonal_winner()
    b.print_winning_board()


def test_diagonal_win() -> None:
    b = Board(width=7, height=6, victory_target=4)
    b.add_move(0, b.o)
    b.add_move(1, b.x)
    b.add_move(1, b.o)
    b.add_move(2, b.x)
    b.add_move(2, b.x)
    b.add_move(2, b.o)
    b.add_move(3, b.x)
    b.add_move(3, b.x)
    b.add_move(3, b.x)
    b.add_move(3, b.o)
    b.check_winner(b.o)
    b.check_winner(b.x)
    b.print_winning_board()


def test_minimax() -> None:
    b = Board(width=7, height=5, victory_target=4)
    MiniMax(b)


def play_vs_ai() -> None:
    board = Board(7, 5, 4)
    board.print_board()

    while not board.is_fully_filled():
        choice = 0

        while choice == 0:
            c = int(input(f"Choose a column to place your {board.x}: "))
            if c <= board.width:
                choice = c
                break

        board.add_move(choice, board.x)
        b = copy.deepcopy(board)
        ai_move = MiniMax(b).minimax(maximizing_player=False)
        board.add_move(ai_move[1], board.o)
        winner = board.get_winner()
        if winner:
            board.print_winning_board()
            break
        board.print_board()


def min_vs_max() -> None:
    board = Board(14, 7, 6)
    board.print_board()
    maximizer = True

    while not board.is_fully_filled():
        # Max
        b = copy.deepcopy(board)
        res = MiniMax(b).minimax(maximizing_player=maximizer)
        maximizer = not maximizer
        ai_move = res[1]
        board.add_move(ai_move, board.x if maximizer else board.o)

        winner = board.get_winner()
        if winner:
            board.print_winning_board()
            break
        board.print_board()


def main() -> None:
    # test_diagonal_win()
    # test_board()
    # test_minimax()
    min_vs_max()
    # play_vs_ai()


if __name__ == "__main__":
    main()
