import math
from datetime import UTC, datetime, timedelta
from os import get_terminal_size
from time import sleep
from typing import override


# https://youtu.be/idHR0xu_xmA for braille char
class ProgressBar:
    # Editable
    space = " "
    message = "Progress:"
    start = "["
    end = "]"
    arrow = ">"
    bar = "="

    def __init__(self, total: int) -> None:
        self._total = total
        self._current = 0
        self._start_time = datetime.now(tz=UTC)

    @property
    def total(self) -> int:
        return self._total

    @property
    def current(self) -> float:
        return self._current

    @current.setter
    def current(self, value: float) -> None:
        self._current = value

    @property
    def scale(self) -> float:
        return self._current / self._total

    def __str__(self) -> str:
        self._MAX_WIDTH = get_terminal_size().columns
        bar_area = self.calculate_bar_area()

        bar_count = self.calculate_bar_count(bar_area)
        bar = self.generate_bar(bar_count)

        space_count = self.calculate_space_count(bar_area, bar)
        space = self.space * space_count

        # if scale == 0, make sure the len our return is the same as any other scale
        end = self.end + self.space if int(self.scale) != 0 else self.end
        return self.build_progress_bar(bar, space, end)

    def build_progress_bar(self, bar: str, space: str, end: str) -> str:
        return f"{self.message}{self.start}{bar}{self.arrow}{space}{end}"

    def calculate_bar_count(self, bar_area: int) -> int:
        return int(bar_area * self.scale)

    def calculate_space_count(self, bar_area: int, bar: str) -> int:
        return (math.floor(bar_area - len(bar)) - len(self.end))

    def calculate_bar_area(self) -> int:
        return (
            self._MAX_WIDTH
            - len(self.message)
            - len(self.start)
            - len(self.arrow)
            - len(self.end)
        )

    def generate_bar(self, bar_count: int) -> str:
        return self.bar * (bar_count // len(self.bar))

    def update(self, current: float) -> None:
        self.current = current

    @property
    def elapsed_time(self) -> timedelta:
        return datetime.now(tz=UTC) - self._start_time

    def reset_timer(self) -> None:
        self._start_time = datetime.now(tz=UTC)

class PreciseProgressBar(ProgressBar):
    _precision = 2
    arrow = ""
    bar = "⠿"

    def __init__(self, total: int) -> None:
        super().__init__(total)
        self.partial_bars = ["⠄","⠆","⠇","⠧","⠷","⠿"]

    @property
    def fraction(self) -> float:
        return round(self.current % 1, self._precision)

    @ProgressBar.current.getter
    def current(self) -> float:
        return self._current

    @current.setter
    def current(self, value: float) -> None:
        self._current = round(value, self._precision)

    @property
    def partial_bar(self) -> str:
        return self._partial_bar

    @partial_bar.setter
    def partial_bar(self, fraction: float) -> None:
        bars_count = len(self.partial_bars)
        target = 1 / bars_count
        index = min(int(fraction / target), bars_count - 1)
        self._partial_bar = self.partial_bars[index]

    @property
    def partial_bars(self) -> list[str]:
        return self._partial_bars

    @partial_bars.setter
    def partial_bars(self, value: list[str]) -> None:
        self._partial_bars = [*value]

    @override
    def update(self, current: float) -> None:
        super().update(current)
        self.partial_bar = self.fraction

    # @property
    # def keep_full(self) -> bool:
    #     # TODO: Find out why 0.25 is super close to working as intended.
    #     # TODO: 0.25 needs to be calculated or based on a variable somewhere.
    #     # return self.current % 1 < (self.fraction/(1/len(self.partial_bars))) # (0.25)
    #     a = self.current % 1
    #     b = self.fraction
    #     c = 1 / len(self.partial_bars)
    #     d = b / c
    #     e = d % 1
    #     return a < e

    @override
    def generate_bar(self, bar_count: int) -> str:
        # if self.keep_full:
        #     return super().generate_bar(bar_count)
        return super().generate_bar(bar_count - 1) + self.partial_bar



def main() -> None:
    while True:
        state = PreciseProgressBar(100)
        # state = ProgressBar(100)
        for i in range(10000):
            state.update(i / 100)
            sleep(0.01)


if __name__ == "__main__":
    main()
