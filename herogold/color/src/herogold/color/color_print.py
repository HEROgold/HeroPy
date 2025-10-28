
from herogold.sentinel import MISSING

class Ansi:
    class Regular:
        Black="\033[0;30m"
        Red="\033[0;31m"
        Green="\033[0;32m"
        Yellow="\033[0;33m"
        Blue="\033[0;34m"
        Purple="\033[0;35m"
        Cyan="\033[0;36m"
        White="\033[0;37m"
        Reset="\033[0m"

    class Bold:
        Black="\033[1;30m"
        Red="\033[1;31m"
        Green="\033[1;32m"
        Yellow="\033[1;33m"
        Blue="\033[1;34m"
        Purple="\033[1;35m"
        Cyan="\033[1;36m"
        White="\033[1;37m"

    class Underline:
        Black="\033[4;30m"
        Red="\033[4;31m"
        Green="\033[4;32m"
        Yellow="\033[4;33m"
        Blue="\033[4;34m"
        Purple="\033[4;35m"
        Cyan="\033[4;36m"
        White="\033[4;37m"

    class Background:
        Black="\033[40m"
        Red="\033[41m"
        Green="\033[42m"
        Yellow="\033[43m"
        Blue="\033[44m"
        Purple="\033[45m"
        Cyan="\033[46m"
        White="\033[47m"

    class HighIntensity:
        Black="\033[0;90m"
        Red="\033[0;91m"
        Green="\033[0;92m"
        Yellow="\033[0;93m"
        Blue="\033[0;94m"
        Purple="\033[0;95m"
        Cyan="\033[0;96m"
        White="\033[0;97m"

    class BoldHighIntensity:
        Black="\033[1;90m"
        Red="\033[1;91m"
        Green="\033[1;92m"
        Yellow="\033[1;93m"
        Blue="\033[1;94m"
        Purple="\033[1;95m"
        Cyan="\033[1;96m"
        White="\033[1;97m"

    class HighIntensityBackgrounds:
        Black="\033[0;100m"
        Red="\033[0;101m"
        Green="\033[0;102m"
        Yellow="\033[0;103m"
        Blue="\033[0;104m"
        Purple="\033[0;105m"
        Cyan="\033[0;106m"
        White="\033[0;107m"


def colorize(color: str, s: str) -> str:
    return f"{color}{s}{Ansi.Regular.Reset}"


class ColorizedString(str):
    def __init__(self, color: str = MISSING) -> None:
        super().__init__()
        if color:
            self = colorize(color, self)


def main() -> None:
    pass


if __name__ == "__main__":
    main()
