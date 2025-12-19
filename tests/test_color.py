from herogold.color.color_print import Regular, colorize

def test_colorize_wraps_text_with_reset() -> None:
    output = colorize(Regular.Green, "hello")
    assert output == f"{Regular.Green}hello{Regular.Reset}"
