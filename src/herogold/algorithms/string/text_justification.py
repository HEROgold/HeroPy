"""Text Justification.

Given an array of words and a max width, format the text such that each line
has exactly max_width characters and is fully justified. Extra spaces are
distributed as evenly as possible with left slots getting more.

Reference: https://leetcode.com/problems/text-justification/

Complexity:
    Time:  O(n) where n is the total number of characters
    Space: O(n)
"""

from __future__ import annotations


def _format_row(
    row_words: list[str], max_width: int, row_length: int, *, is_last_row: bool,
) -> str:
    """Helper to format a single row for text justification."""
    if is_last_row:
        row = " ".join(row_words)
        row += " " * (max_width - len(row))
        return row
    if len(row_words) == 1:
        return row_words[0] + " " * (max_width - len(row_words[0]))
    extra_spaces = max_width - row_length
    spaces_per_gap = extra_spaces // (len(row_words) - 1)
    remaining_spaces = extra_spaces - spaces_per_gap * (len(row_words) - 1)
    row = ""
    for word_index, word in enumerate(row_words):
        row += word
        if word_index != len(row_words) - 1:
            row += " " * (1 + spaces_per_gap)
            if remaining_spaces > 0:
                row += " "
                remaining_spaces -= 1
    return row

def text_justification(words: list[str], max_width: int) -> list[str]:
    """Justify text to a fixed width with evenly distributed spaces.

    Args:
        words: A list of words to justify.
        max_width: The maximum width of each line.

    Returns:
        A list of fully justified strings.

    Raises:
        ValueError: If any word is longer than max_width.

    Examples:
        >>> text_justification(["What", "must", "be"], 16)
        ['What   must   be']

    """
    result: list[str] = []
    row_length = 0
    row_words: list[str] = []
    index = 0
    is_first_word = True

    while index < len(words):
        while row_length <= max_width and index < len(words):
            if len(words[index]) > max_width:
                msg = "there exists word whose length is larger than max_width"
                raise ValueError(msg)
            tentative_length = row_length
            row_words.append(words[index])
            tentative_length += len(words[index])
            if not is_first_word:
                tentative_length += 1
            if tentative_length > max_width:
                row_words.pop()
                break
            row_length = tentative_length
            index += 1
        is_last_row = index == len(words)
        result.append(_format_row(row_words, max_width, row_length, is_last_row=is_last_row))
        row_length = 0
        row_words = []
        is_first_word = True
        row_words = []
        is_first_word = True

    return result
