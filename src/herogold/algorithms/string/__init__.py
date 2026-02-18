"""String algorithms package."""

from __future__ import annotations

from herogold.algorithms.string import fizzbuzz
from herogold.algorithms.string.add_binary import add_binary
from herogold.algorithms.string.alphabet_board_path import alphabet_board_path
from herogold.algorithms.string.atbash_cipher import atbash
from herogold.algorithms.string.breaking_bad import bracket, match_symbol, match_symbol_1
from herogold.algorithms.string.caesar_cipher import caesar_cipher
from herogold.algorithms.string.check_pangram import check_pangram
from herogold.algorithms.string.contain_string import contain_string
from herogold.algorithms.string.count_binary_substring import count_binary_substring
from herogold.algorithms.string.decode_string import decode_string
from herogold.algorithms.string.delete_reoccurring import delete_reoccurring_characters
from herogold.algorithms.string.domain_extractor import domain_name_1, domain_name_2
from herogold.algorithms.string.encode_decode import decode, encode
from herogold.algorithms.string.first_unique_char import first_unique_char
from herogold.algorithms.string.fizzbuzz import fizzbuzz_with_helper_func
from herogold.algorithms.string.group_anagrams import group_anagrams
from herogold.algorithms.string.int_to_roman import int_to_roman
from herogold.algorithms.string.is_palindrome import (
    is_palindrome,
    is_palindrome_deque,
    is_palindrome_reverse,
    is_palindrome_stack,
    is_palindrome_two_pointer,
)
from herogold.algorithms.string.is_rotated import is_rotated, is_rotated_v1
from herogold.algorithms.string.judge_circle import judge_circle
from herogold.algorithms.string.knuth_morris_pratt import knuth_morris_pratt
from herogold.algorithms.string.license_number import license_number
from herogold.algorithms.string.longest_common_prefix import (
    longest_common_prefix_v1,
    longest_common_prefix_v2,
    longest_common_prefix_v3,
)
from herogold.algorithms.string.longest_palindromic_substring import longest_palindrome
from herogold.algorithms.string.make_sentence import make_sentence
from herogold.algorithms.string.manacher import manacher
from herogold.algorithms.string.merge_string_checker import is_merge_iterative, is_merge_recursive
from herogold.algorithms.string.min_distance import min_distance, min_distance_dp
from herogold.algorithms.string.multiply_strings import multiply
from herogold.algorithms.string.one_edit_distance import is_one_edit, is_one_edit2
from herogold.algorithms.string.panagram import panagram
from herogold.algorithms.string.rabin_karp import RollingHash, rabin_karp
from herogold.algorithms.string.repeat_string import repeat_string
from herogold.algorithms.string.repeat_substring import repeat_substring
from herogold.algorithms.string.reverse_string import iterative, pythonic, recursive, ultra_pythonic
from herogold.algorithms.string.reverse_vowel import reverse_vowel
from herogold.algorithms.string.reverse_words import reverse_words
from herogold.algorithms.string.roman_to_int import roman_to_int
from herogold.algorithms.string.rotate import rotate, rotate_alt
from herogold.algorithms.string.strip_url_params import strip_url_params1, strip_url_params2, strip_url_params3
from herogold.algorithms.string.strong_password import strong_password
from herogold.algorithms.string.swap_characters import can_swap_to_equal
from herogold.algorithms.string.text_justification import text_justification
from herogold.algorithms.string.unique_morse import convert_morse_word, unique_morse
from herogold.algorithms.string.validate_coordinates import (
    is_valid_coordinates_0,
    is_valid_coordinates_1,
    is_valid_coordinates_regular_expression,
)
from herogold.algorithms.string.word_squares import word_squares
from herogold.algorithms.string.z_algorithm import compute_z_array, z_search

__all__ = [
    "RollingHash",
    "add_binary",
    "alphabet_board_path",
    "atbash",
    "bracket",
    "caesar_cipher",
    "can_swap_to_equal",
    "check_pangram",
    "compute_z_array",
    "contain_string",
    "convert_morse_word",
    "count_binary_substring",
    "decode",
    "decode_string",
    "delete_reoccurring_characters",
    "domain_name_1",
    "domain_name_2",
    "encode",
    "first_unique_char",
    "fizzbuzz",
    "fizzbuzz_with_helper_func",
    "group_anagrams",
    "int_to_roman",
    "is_merge_iterative",
    "is_merge_recursive",
    "is_one_edit",
    "is_one_edit2",
    "is_palindrome",
    "is_palindrome_deque",
    "is_palindrome_reverse",
    "is_palindrome_stack",
    "is_palindrome_two_pointer",
    "is_rotated",
    "is_rotated_v1",
    "is_valid_coordinates_0",
    "is_valid_coordinates_1",
    "is_valid_coordinates_regular_expression",
    "iterative",
    "judge_circle",
    "knuth_morris_pratt",
    "license_number",
    "longest_common_prefix_v1",
    "longest_common_prefix_v2",
    "longest_common_prefix_v3",
    "longest_palindrome",
    "make_sentence",
    "manacher",
    "match_symbol",
    "match_symbol_1",
    "min_distance",
    "min_distance_dp",
    "multiply",
    "panagram",
    "pythonic",
    "rabin_karp",
    "recursive",
    "repeat_string",
    "repeat_substring",
    "reverse_vowel",
    "reverse_words",
    "roman_to_int",
    "rotate",
    "rotate_alt",
    "strip_url_params1",
    "strip_url_params2",
    "strip_url_params3",
    "strong_password",
    "text_justification",
    "ultra_pythonic",
    "unique_morse",
    "word_squares",
    "z_search",
]
