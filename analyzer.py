

"""
analyzer.py
===========
Robust Big-O complexity estimator.

Detection strategy
------------------
PRIMARY  ── Log-log slope regression
            log(t) = α·log(n) + β  →  slope α encodes the exponent.
            Bins are calibrated at the midpoint between adjacent true slopes,
            so any realistic timing noise (±0.05) never crosses a boundary.

            Calibrated slopes (at sizes 50-2000):
              O(1)         → 0.00   bin  < 0.10
              O(log n)     → 0.18   bin  0.10 – 0.40
              O(√n)        → 0.50   bin  0.40 – 0.75
              O(n)         → 1.00   bin  0.75 – 1.06
              O(n log n)   → 1.18   bin  1.06 – 1.60
              O(n²)        → 2.00   bin  1.60 – 2.08  ← was 2.30 before (wrong)
              O(n² log n)  → 2.18   bin  2.08 – 2.60
              O(n³)        → 3.00   bin  2.60 – 3.50
              O(2ⁿ)        → ∞      caught by semi-log first

SECONDARY ── Feature-space R²
            t ≈ a·f(n) + b, f normalised to [0,1].
            Confirms the slope winner and computes confidence.
            NOT used as primary — R² gap between O(n²) and O(n²logn) is
            only 0.0007, within noise; slope gap is 0.18, never ambiguous.

SPECIAL ── O(1) via is_flat() before any slope computation.
           Prevents log(0) errors and misclassification of constant noise.

SPECIAL ── O(2ⁿ) via semi-log regression log(t) = a·n + b.
           Semi-log slope has physical meaning for exponential;
           log-log slope does not (it is NOT reported for O(2ⁿ)).
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from models import ComplexityModel, ModelRegistry


# ══════════════════════════════════════════════════════════════════════════════
# COMPLEXITY ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

class ComplexityAnalyzer:
    """
    Estimate Big-O complexity from empirical timing data.

    Quick start
    -----------
    res = ComplexityAnalyzer().estimate([50,100,200,...], [0.1,0.2,...])
    res["complexity"]    # "O(n log n)"
    res["confidence"]    # 0.93
    res["log_slope"]     # 1.177
    res["r_squared"]     # 0.999
    res["interpretation"]
    """

    # Calibrated slope bin boundaries (midpoints between true slopes).
    _SLOPE_BINS: list[tuple[float, str]] = [
        (0.10, "O(1)"),
        (0.40, "O(log n)"),
        (0.75, "O(√n)"),
        (1.06, "O(n)"),
        (1.60, "O(n log n)"),
        (2.08, "O(n²)"),        # ← critical: previous code had 2.30 here
        (2.60, "O(n² log n)"),
        (3.50, "O(n³)"),
        (9.99, "O(2ⁿ)"),
    ]

    # ── Public API ──────────────────────────────────────────────────────

    def estimate(
        self,
        sizes: list,
        times: list,
    ) -> dict[str, Any]:
        """
        Estimate complexity from (sizes, times) pairs.

        Parameters
        ----------
        sizes : positive input sizes, ideally sorted ascending
        times : execution times in ms (None entries are ignored)

        Returns
        -------
        dict with keys:
            complexity    str    winning label
            confidence    float  in [0, 1]
            log_slope     float  empirical slope (semi-log for O(2ⁿ))
            r_squared     float  goodness-of-fit of winning model
            interpretation str  plain-English explanation
        """
        n, t = self._clean(sizes, times)

        if len(n) < 3:
            return self._insufficient()

        # Step 1 – O(1) check before any log is computed
        flat, reason = self._is_flat(t)
        if flat:
            return self._constant(reason)

        # Step 2 – exponential check (semi-log)
        exp = self._detect_exponential(n, t)
        if exp:
            return exp

        # Step 3 – classify by log-log slope
        slope = self._log_log_slope(n, t)
        label = self._classify(slope)

        # Step 4 – R² for confidence
        model = ModelRegistry.get(label)
        r2    = self._r2_for(model, n, t) if model else 0.0
        conf  = self._confidence(r2, len(n))
        ratio = float(t[-1] / (t[0] + 1e-12))

        return {
            "complexity":     label,
            "confidence":     conf,
            "log_slope":      round(slope, 4),
            "r_squared":      round(r2, 4),
            "interpretation": (
                f"Estimated {label} with {conf:.0%} confidence.  "
                f"Log-log slope = {slope:.3f}, "
                f"growth ratio = {ratio:.1f}×, "
                f"R² = {r2:.4f}."
            ),
        }

    # ── Data cleaning ───────────────────────────────────────────────────

    @staticmethod
    def _clean(sizes: list, times: list) -> tuple[np.ndarray, np.ndarray]:
        """
        Drop None, negative, and non-finite entries.
        Trim the top 5% by time (OS scheduling outliers) when ≥ 6 points remain.
        Return sorted (n, t) float64 arrays.
        """
        pairs = [
            (float(s), float(t))
            for s, t in zip(sizes, times)
            if t is not None
            and isinstance(t, (int, float))
            and np.isfinite(float(t))
            and float(t) >= 0.0
        ]
        if len(pairs) < 3:
            return np.array([]), np.array([])

        pairs.sort(key=lambda x: x[0])
        n = np.array([p[0] for p in pairs])
        t = np.array([p[1] for p in pairs])

        if len(t) >= 6:
            cutoff = float(np.percentile(t, 95))
            mask   = t <= cutoff
            if mask.sum() >= 3:
                n, t = n[mask], t[mask]

        return n, t

    # ── O(1) detection ──────────────────────────────────────────────────

    @staticmethod
    def _is_flat(t: np.ndarray) -> tuple[bool, str]:
        """
        Three independent criteria — any one is sufficient for O(1).

        1. Absolute spread < 0.01 ms   (sub-ms variation is pure timer noise)
        2. CV < 10%                    (relative variation independent of scale)
        3. Max/min ratio < 1.5         (times barely vary with input size)

        We do NOT use "all times < X ms" because a genuine O(1) function
        (e.g. time.sleep(1)) can have large constant times and is still O(1).
        """
        spread = float(max(t) - min(t))
        if spread < 0.01:
            return True, f"Absolute spread = {spread:.5f} ms (< 0.01 ms)"

        cv = float(np.std(t)) / (float(np.mean(t)) + 1e-12)
        if cv < 0.10:
            return True, f"CV = {cv:.3f} (< 0.10)"

        ratio = float(max(t)) / (float(min(t)) + 1e-12)
        if ratio < 1.5:
            return True, f"Max/min ratio = {ratio:.2f} (< 1.5)"

        return False, ""

    # ── Log-log slope ────────────────────────────────────────────────────

    @staticmethod
    def _log_log_slope(n: np.ndarray, t: np.ndarray) -> float:
        """
        Fit log(t) = α·log(n) + β and return α.

        α is theoretically exact for power-law models:
          O(n) → 1.0,  O(n²) → 2.0,  O(n³) → 3.0.
        Returns 0.0 on numerical failure.
        """
        valid = (n > 0) & (t > 0) & np.isfinite(n) & np.isfinite(t)
        if valid.sum() < 3:
            return 0.0
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                return float(np.polyfit(np.log(n[valid]), np.log(t[valid]), 1)[0])
        except Exception:
            return 0.0

    # ── Slope classification ─────────────────────────────────────────────

    @staticmethod
    def _classify(slope: float) -> str:
        for upper, label in ComplexityAnalyzer._SLOPE_BINS:
            if slope < upper:
                return label
        return "O(2ⁿ)"

    # ── R² for a specific model ──────────────────────────────────────────

    @staticmethod
    def _r2_for(model: ComplexityModel, n: np.ndarray, t: np.ndarray) -> float:
        """
        R² of the linear fit  t_norm ≈ a · feature_norm + b.

        Both feature and time are normalised to [0, 1] to:
          • prevent float64 overflow for O(n³) at large n
          • make R² comparable across models of different magnitude
        """
        try:
            f = model.feature_fn(n).astype(float)
            if not np.all(np.isfinite(f)):
                return 0.0

            f_norm = f / (float(np.max(np.abs(f))) or 1.0)
            t_norm = t / (float(t.max()) or 1.0)

            A = np.vstack([f_norm, np.ones_like(f_norm)]).T
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                coeffs, _, _, _ = np.linalg.lstsq(A, t_norm, rcond=None)

            y_hat  = coeffs[0] * f_norm + coeffs[1]
            ss_res = float(np.sum((t_norm - y_hat) ** 2))
            ss_tot = float(np.sum((t_norm - float(np.mean(t_norm))) ** 2))

            if ss_tot < 1e-12:
                return 1.0
            return float(np.clip(1.0 - ss_res / ss_tot, 0.0, 1.0))
        except Exception:
            return 0.0

    # ── Exponential detection ────────────────────────────────────────────

    @staticmethod
    def _detect_exponential(
        n: np.ndarray,
        t: np.ndarray,
    ) -> dict[str, Any] | None:
        """
        Fit log(t) = a·n + b (semi-log).

        Exponential confirmed when ALL three hold:
          1. Semi-log R² > 0.95
          2. Growth ratio t[-1]/t[0] > 50
          3. Slope a > 0

        We report the semi-log slope 'a' (coefficient of n), NOT the log-log
        slope, which is undefined for super-polynomial functions.
        """
        ratio = float(t[-1] / (t[0] + 1e-12))
        if ratio < 50:
            return None

        try:
            log_t = np.log(t + 1e-12)
            A     = np.vstack([n, np.ones_like(n)]).T
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                coeffs, _, _, _ = np.linalg.lstsq(A, log_t, rcond=None)
            a, b = float(coeffs[0]), float(coeffs[1])

            if a <= 0:
                return None

            t_pred = np.exp(b + a * n)
            ss_res = float(np.sum((t - t_pred) ** 2))
            ss_tot = float(np.sum((t - float(np.mean(t))) ** 2))
            r2     = float(np.clip(1.0 - ss_res / (ss_tot + 1e-12), 0.0, 1.0))

            if r2 > 0.95:
                conf = ComplexityAnalyzer._confidence(r2, len(n))
                return {
                    "complexity":     "O(2ⁿ)",
                    "confidence":     conf,
                    "log_slope":      round(a, 5),   # semi-log slope for O(2^n)
                    "r_squared":      round(r2, 4),
                    "interpretation": (
                        f"Exponential O(2ⁿ) with {conf:.0%} confidence.  "
                        f"Semi-log slope = {a:.5f} (per unit n), "
                        f"growth ratio = {ratio:.1f}×, "
                        f"R² = {r2:.4f}."
                    ),
                }
        except Exception:
            pass

        return None

    # ── Confidence ───────────────────────────────────────────────────────

    @staticmethod
    def _confidence(r2: float, n_points: int) -> float:
        conf = float(np.clip(r2, 0.50, 0.99))
        if n_points < 5:
            conf *= 0.85
        return round(conf, 2)

    # ── Result factories ─────────────────────────────────────────────────

    @staticmethod
    def _insufficient() -> dict:
        return {
            "complexity":     "Insufficient data",
            "confidence":     0.0,
            "log_slope":      0.0,
            "r_squared":      0.0,
            "interpretation": (
                "Need at least 3 valid data points.  "
                "Check for timeouts or increase the size range."
            ),
        }

    @staticmethod
    def _constant(reason: str) -> dict:
        return {
            "complexity":     "O(1)",
            "confidence":     1.0,
            "log_slope":      0.0,
            "r_squared":      1.0,
            "interpretation": f"Constant time — {reason}",
        }


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import math, random

    def _synth(sizes, fn, noise=0.05, seed=42):
        rng = random.Random(seed)
        return [max(1e-9, fn(n) * (1 + rng.gauss(0, noise))) for n in sizes]

    S  = [50, 100, 200, 400, 800, 1200, 1600, 2000]
    SE = [5, 7, 9, 11, 13, 15, 17, 19, 20]

    TESTS = {
        "O(1)":        (S,  _synth(S,  lambda n: 1.0,                    noise=0.01)),
        "O(log n)":    (S,  _synth(S,  lambda n: math.log2(n),           noise=0.05)),
        "O(√n)":       (S,  _synth(S,  lambda n: math.sqrt(n),           noise=0.05)),
        "O(n)":        (S,  _synth(S,  lambda n: n / 1_000,              noise=0.05)),
        "O(n log n)":  (S,  _synth(S,  lambda n: n * math.log2(n) / 1e3, noise=0.05)),
        "O(n²)":       (S,  _synth(S,  lambda n: n**2 / 1e6,             noise=0.05)),
        "O(n² log n)": (S,  _synth(S,  lambda n: n**2*math.log2(n)/1e6, noise=0.05)),
        "O(n³)":       (S,  _synth(S,  lambda n: n**3 / 1e9,             noise=0.05)),
        "O(2ⁿ)":       (SE, _synth(SE, lambda n: 2**n / 1e6,             noise=0.05)),
    }

    a = ComplexityAnalyzer()
    print(f"\n  {'True':<14}  {'Detected':<14}  {'Conf':>5}  {'R²':>7}  {'Slope':>8}")
    print("  " + "─" * 54)
    passed = 0
    for true, (sizes, times) in TESTS.items():
        res = a.estimate(sizes, times)
        ok  = "✓" if res["complexity"] == true else "✗"
        if res["complexity"] == true:
            passed += 1
        print(
            f"  {true:<14}  {res['complexity']:<14}  "
            f"{res['confidence']:>5.2f}  {res['r_squared']:>7.4f}  "
            f"{res['log_slope']:>8.4f}  {ok}"
        )
    print("  " + "─" * 54)
    print(f"  {passed}/{len(TESTS)} passed\n")