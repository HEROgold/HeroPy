from herogold.color.color_print import Ansi, colorize

def test_colorize_wraps_text_with_reset() -> None:
    output = colorize(Ansi.Regular.Green, "hello")
    assert output == f"{Ansi.Regular.Green}hello{Ansi.Regular.Reset}"
