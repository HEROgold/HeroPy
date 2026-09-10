"""Ten levels of nested subcommands: 10 -> 9 -> 8 -> ... -> 1."""

from __future__ import annotations

from herogold.argparse import Argument, Namespace, entrypoint


class Root(Namespace):
    """Root of a ten-level-deep subcommand chain."""


class Level10(Root, subcommand="10"):
    """Level 10."""


class Level9(Level10, subcommand="9"):
    """Level 9."""


class Level8(Level9, subcommand="8"):
    """Level 8."""


class Level7(Level8, subcommand="7"):
    """Level 7."""


class Level6(Level7, subcommand="6"):
    """Level 6."""


class Level5(Level6, subcommand="5"):
    """Level 5."""


class Level4(Level5, subcommand="4"):
    """Level 4."""


class Level3(Level4, subcommand="3"):
    """Level 3."""


class Level2(Level3, subcommand="2"):
    """Level 2."""


class Level1(Level2, subcommand="1"):
    """Level 1, the deepest subcommand."""

    message = Argument("message", help="Message to print at the bottom", default="reached the bottom")


@entrypoint(Root)
def main(options: Root) -> None:
    print("Resolved class:", type(options).__name__)
    if isinstance(options, Level1):
        print("message =", options.message)


if __name__ == "__main__":
    main()
