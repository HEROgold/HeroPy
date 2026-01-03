"""A simple progress bar for terminal output."""

import math
from datetime import UTC, datetime, timedelta
from os import get_terminal_size
from time import sleep
from typing import ClassVar, override


# https://youtu.be/idHR0xu_xmA for braille char
class ProgressBar:
    """A simple progress bar for terminal output."""

    # Editable
    precision = 2
    space = " "
    prefix = "Progress:"
    start = "["
    end = "]"
    arrow = ">"
    bar = "="

    def __init__(self, total: int) -> None:
        """Create a progress bar instance, with a total number of steps. This is the 100% marker."""
        self._total = total
        self._current = 0
        self._start_time = datetime.now(tz=UTC)

    @property
    def progress_percent(self) -> str:
        """Return the current progress as a percentage."""
        return f"{(self.current / self.total):.{self.precision}%}"

    @property
    def message(self) -> str:
        """Return the progress message prefix."""
        return f"{self.prefix} {self.progress_percent} "

    @property
    def total(self) -> int:
        """Return the total number of steps for the progress bar."""
        return self._total

    @property
    def current(self) -> float:
        """Return the current progress value."""
        return self._current

    @current.setter
    def current(self, value: float) -> None:
        self._current = value

    @property
    def scale(self) -> float:
        """Return the current progress as a fraction of the total."""
        return self._current / self._total

    def __str__(self) -> str:
        """Return the string representation of the progress bar."""
        bar_area = self.calculate_bar_area()

        bar_count = self.calculate_bar_count(bar_area)
        bar = self.generate_bar(int(bar_count))

        space_count = self.calculate_space_count(bar_area, bar)
        space = self.space * space_count

        return self.build_progress_bar(bar, space)

    def build_progress_bar(self, bar: str, space: str) -> str:
        """Build and return the complete progress bar string."""
        return f"{self.message}{self.start}{bar}{self.arrow}{space}{self.end}"

    def calculate_bar_count(self, bar_area: int) -> float:
        """Calculate the number of characters to use for the progress bar based on the current scale."""
        # Clamp scale between 0 and 1. Avoiding over/under flow.
        return bar_area * max(min(1, self.scale), 0)

    def calculate_space_count(self, bar_area: int, bar: str) -> int:
        """Calculate the number of spaces to use in the progress bar."""
        return (math.floor(bar_area - len(bar)) - len(self.end))

    def calculate_bar_area(self) -> int:
        """Calculate the available width for the progress bar."""
        return (
            get_terminal_size().columns
            - len(self.message)
            - len(self.start)
            - len(self.arrow)
            - len(self.end)
        )

    def generate_bar(self, bar_count: int) -> str:
        """Generate the progress bar string based on the number of characters."""
        return self.bar * bar_count

    def update(self, current: float) -> None:
        """Update the current progress value."""
        self.current = current

    @property
    def elapsed_time(self) -> timedelta:
        """Return the elapsed time since the progress bar was started."""
        return datetime.now(tz=UTC) - self._start_time

    def reset_timer(self) -> None:
        """Reset the start time to the current time."""
        self._start_time = datetime.now(tz=UTC)

class PreciseProgressBar(ProgressBar):
    """A progress bar that supports fractional progress with specified precision."""

    arrow = ""
    bar = "⠿"
    partial_bars: ClassVar[list[str]] = ["⠄","⠆","⠇","⠧","⠷","⠿"]

    @ProgressBar.current.setter
    def current(self, value: float) -> None:
        """Set the current progress value, rounding to the specified precision."""
        self._current = round(value, self.precision)

    def get_partial_bar(self) -> str:
        """Get the appropriate partial bar character based on the fractional progress."""
        if self.current >= self.total:
            return ""

        bar_area = self.calculate_bar_area()
        bar_count = self.calculate_bar_count(bar_area)
        frac = bar_count % 1

        index = min(
            int(frac * len(self.partial_bars)),
            len(self.partial_bars) - 1,
        )
        return self.partial_bars[index]

    @override
    def update(self, current: float) -> None:
        super().update(current)
        self.partial_bar = self.get_partial_bar()

    @override
    def generate_bar(self, bar_count: int) -> str:
        return super().generate_bar(bar_count) + self.partial_bar


def main() -> None:
    """Demonstrate the progress bar functionality."""
    while True:
        state = PreciseProgressBar(100)
        for i in range(10000):
            state.update(i)
            print(state, end="\r")  # noqa: T201
            sleep(0.1)


if __name__ == "__main__":
    main()
