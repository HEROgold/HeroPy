"""Collection of mathematical algorithms and functions."""

from __future__ import annotations

# Module-level imports for backward compatibility (tests use module.function syntax)
from herogold.algorithms.math import chinese_remainder_theorem, fft, hailstone, modular_inverse
from herogold.algorithms.math.base_conversion import base_to_int, int_to_base
from herogold.algorithms.math.combination import combination, combination_memo
from herogold.algorithms.math.cosine_similarity import cosine_similarity
from herogold.algorithms.math.decimal_to_binary_ip import decimal_to_binary_ip, decimal_to_binary_util
from herogold.algorithms.math.diffie_hellman_key_exchange import (
    alice_private_key,
    alice_public_key,
    alice_shared_key,
    bob_private_key,
    bob_public_key,
    bob_shared_key,
    diffie_hellman_key_exchange,
)
from herogold.algorithms.math.distance_between_two_points import distance_between_two_points
from herogold.algorithms.math.euler_totient import euler_totient
from herogold.algorithms.math.extended_gcd import extended_gcd
from herogold.algorithms.math.factorial import factorial, factorial_recur
from herogold.algorithms.math.find_order_simple import find_order
from herogold.algorithms.math.find_primitive_root_simple import find_primitive_root
from herogold.algorithms.math.gcd import gcd, gcd_bit, lcm, trailing_zero
from herogold.algorithms.math.generate_strobogrammtic import gen_strobogrammatic, strobogrammatic_in_range
from herogold.algorithms.math.goldbach import goldbach, verify_goldbach
from herogold.algorithms.math.is_strobogrammatic import is_strobogrammatic, is_strobogrammatic2
from herogold.algorithms.math.krishnamurthy_number import krishnamurthy_number
from herogold.algorithms.math.linear_regression import linear_regression, r_squared, rmse
from herogold.algorithms.math.magic_number import magic_number
from herogold.algorithms.math.manhattan_distance import manhattan_distance
from herogold.algorithms.math.modular_exponential import modular_exponential
from herogold.algorithms.math.next_bigger import next_bigger
from herogold.algorithms.math.next_perfect_square import find_next_square, find_next_square2
from herogold.algorithms.math.nth_digit import find_nth_digit
from herogold.algorithms.math.num_digits import num_digits
from herogold.algorithms.math.num_perfect_squares import num_perfect_squares
from herogold.algorithms.math.power import power, power_recur
from herogold.algorithms.math.prime_check import prime_check
from herogold.algorithms.math.primes_sieve_of_eratosthenes import get_primes
from herogold.algorithms.math.pythagoras import pythagoras
from herogold.algorithms.math.rabin_miller import is_prime
from herogold.algorithms.math.recursive_binomial_coefficient import recursive_binomial_coefficient
from herogold.algorithms.math.rsa import decrypt, encrypt, generate_key
from herogold.algorithms.math.sqrt_precision_factor import square_root
from herogold.algorithms.math.summing_digits import sum_dig_pow
from herogold.algorithms.math.surface_area_of_torus import surface_area_of_torus

__all__ = [
    "alice_private_key",
    "alice_public_key",
    "alice_shared_key",
    "base_to_int",
    "bob_private_key",
    "bob_public_key",
    "bob_shared_key",
    "chinese_remainder_theorem",
    "combination",
    "combination_memo",
    "cosine_similarity",
    "decimal_to_binary_ip",
    "decimal_to_binary_util",
    "decrypt",
    "diffie_hellman_key_exchange",
    "distance_between_two_points",
    "encrypt",
    "euler_totient",
    "extended_gcd",
    "factorial",
    "factorial_recur",
    "fft",
    "find_next_square",
    "find_next_square2",
    "find_nth_digit",
    "find_order",
    "find_primitive_root",
    "gcd",
    "gcd_bit",
    "gen_strobogrammatic",
    "generate_key",
    "get_primes",
    "goldbach",
    "hailstone",
    "int_to_base",
    "is_prime",
    "is_strobogrammatic",
    "is_strobogrammatic2",
    "krishnamurthy_number",
    "lcm",
    "linear_regression",
    "magic_number",
    "manhattan_distance",
    "modular_exponential",
    "modular_inverse",
    "next_bigger",
    "num_digits",
    "num_perfect_squares",
    "power",
    "power_recur",
    "prime_check",
    "pythagoras",
    "r_squared",
    "recursive_binomial_coefficient",
    "rmse",
    "square_root",
    "strobogrammatic_in_range",
    "sum_dig_pow",
    "surface_area_of_torus",
    "trailing_zero",
    "verify_goldbach",
]
