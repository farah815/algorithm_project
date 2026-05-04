"""
models.py
=========
Defines all supported Big-O complexity classes.

Add or remove complexity models here only;
no other file needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class ComplexityModel:
    """
    Immutable descriptor for one Big-O class.

    name           : display label
    feature_fn     : maps n (float64 array) → feature array for regression
    is_exponential : True only for O(2ⁿ); uses semi-log fit instead of log-log
    order          : tie-breaking priority (lower = simpler preferred)
    """
    name:           str
    feature_fn:     Callable[[np.ndarray], np.ndarray]
    is_exponential: bool = False
    order:          int  = 0


class ModelRegistry:
    """
    Single source of truth for all supported complexity classes.
    """

    MODELS: list[ComplexityModel] = [
        ComplexityModel("O(1)",
            lambda n: np.ones_like(n, dtype=float), order=0),
        ComplexityModel("O(log n)",
            lambda n: np.log2(np.maximum(n, 2.0)), order=1),
        ComplexityModel("O(√n)",
            lambda n: np.sqrt(n), order=2),
        ComplexityModel("O(n)",
            lambda n: n.astype(float), order=3),
        ComplexityModel("O(n log n)",
            lambda n: n * np.log2(np.maximum(n, 2.0)), order=4),
        ComplexityModel("O(n²)",
            lambda n: n ** 2, order=5),
        ComplexityModel("O(n² log n)",
            lambda n: (n ** 2) * np.log2(np.maximum(n, 2.0)), order=6),
        ComplexityModel("O(n³)",
            lambda n: n ** 3, order=7),
        ComplexityModel("O(2ⁿ)",
            lambda n: 2.0 ** np.minimum(n, 30.0),
            is_exponential=True, order=8),
    ]

    @classmethod
    def get_all(cls) -> list[ComplexityModel]:
        return cls.MODELS

    @classmethod
    def get(cls, name: str) -> ComplexityModel | None:
        return next((m for m in cls.MODELS if m.name == name), None)