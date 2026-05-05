"""
data_generator.py
=================
Input array generation for algorithm testing.

- Manual mode : parse user string → list
- Auto mode   : generate best / average / worst arrays
- Debug suite : synthetic timing data for self-test
"""

import math
import random


# ── Debug suite (synthetic timing data) ─────────────────────────────────────

def _synth(sizes, fn, noise=0.05, seed=42):
    rng = random.Random(seed)
    return [max(1e-9, fn(n) * (1 + rng.gauss(0, noise))) for n in sizes]

_S  = [50, 100, 200, 400, 800, 1200, 1600, 2000]
_SE = [5, 7, 9, 11, 13, 15, 17, 19, 20]

DEBUG_SUITE = {
    "O(1)":        (_S,  _synth(_S,  lambda n: 1.0,                     noise=0.01)),
    "O(log n)":    (_S,  _synth(_S,  lambda n: math.log2(n),            noise=0.05)),
    "O(√n)":       (_S,  _synth(_S,  lambda n: math.sqrt(n),            noise=0.05)),
    "O(n)":        (_S,  _synth(_S,  lambda n: n / 1_000,               noise=0.05)),
    "O(n log n)":  (_S,  _synth(_S,  lambda n: n * math.log2(n) / 1e3,  noise=0.05)),
    "O(n²)":       (_S,  _synth(_S,  lambda n: n**2 / 1e6,              noise=0.05)),
    "O(n² log n)": (_S,  _synth(_S,  lambda n: n**2 * math.log2(n)/1e6, noise=0.05)),
    "O(n³)":       (_S,  _synth(_S,  lambda n: n**3 / 1e9,              noise=0.05)),
    "O(2ⁿ)":       (_SE, _synth(_SE, lambda n: 2**n / 1e6,              noise=0.05)),
}


# ── Data generation ──────────────────────────────────────────────────────────

def make_data(n: int, case: str) -> list:
    """
    Generate an array of size n for best / average / worst case.

    Parameters
    ----------
    n    : array size
    case : "best", "average", or "worst"

    Returns
    -------
    list of int
    """
    if case == "best":
        return list(range(n))
    if case == "worst":
        return list(range(n, 0, -1))
    arr = list(range(n))
    random.shuffle(arr)
    return arr


def parse_manual_input(user_input: str) -> list:
    """
    Parse a comma-separated string into a list of integers.

    Parameters
    ----------
    user_input : e.g. "5, 3, 8, 1, 9"

    Returns
    -------
    list of int

    Raises
    ------
    ValueError if the string cannot be parsed.
    """
    try:
        arr = [int(x.strip()) for x in user_input.split(",") if x.strip()]
        if not arr:
            raise ValueError("Empty input")
        return arr
    except ValueError as e:
        raise ValueError(
            f"Invalid input: {e}. "
            "Please enter comma-separated integers, e.g. 5, 3, 8, 1, 9"
        )