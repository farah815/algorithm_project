import numpy as np


class Analyzer:
    """
    Estimates algorithmic complexity by fitting timing data to canonical
    Big-O models using linear regression in the transformed (feature) space.

    Strategy
    --------
    For each model f(n), we define a feature x = f(n) and fit
        t ≈ a·x + b
    using numpy.polyfit (ordinary least squares).  The model that produces
    the highest R² is reported as the estimated complexity.

    All arrays are normalised before fitting to avoid numerical overflow
    and to make R² values comparable across models.
    """

    # (label, feature function n→x)
    MODELS = [
        ("O(1)",        lambda n: np.ones_like(n)),
        ("O(log n)",    lambda n: np.log2(n)),
        ("O(√n)",       lambda n: np.sqrt(n)),
        ("O(n)",        lambda n: n.copy()),
        ("O(n log n)",  lambda n: n * np.log2(n)),
        ("O(n²)",       lambda n: n ** 2),
        ("O(n² log n)", lambda n: n ** 2 * np.log2(n)),
        ("O(n³)",       lambda n: n ** 3),
        ("O(2ⁿ)",       lambda n: 2.0 ** n),
    ]

    # ------------------------------------------------------------------
    @staticmethod
    def _r_squared(y: np.ndarray, y_hat: np.ndarray) -> float:
        ss_res = float(np.sum((y - y_hat) ** 2))
        ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
        if ss_tot == 0.0:
            return 1.0 if ss_res < 1e-12 else 0.0
        return 1.0 - ss_res / ss_tot

    # ------------------------------------------------------------------
    def estimate(self, sizes: list, times: list) -> dict:
        """
        Parameters
        ----------
        sizes : list[int]   – input sizes (must be sorted ascending)
        times : list[float] – corresponding average execution times (ms)

        Returns
        -------
        dict with keys:
            complexity  str    – e.g. "O(n log n)"
            slope       float  – fitted coefficient a (normalised)
            r_squared   float  – goodness-of-fit of the winning model
            all_scores  dict   – {label: r²} for all models (for debugging)
        """
        n = np.array(sizes, dtype=float)
        t = np.array(times, dtype=float)

        # ── Guard: almost flat execution time → O(1) ──────────────────
        mean_t = float(np.mean(t)) or 1e-12
        if float(np.std(t)) / mean_t < 0.05:
            return {
                "complexity": "O(1)",
                "slope":      0.0,
                "r_squared":  1.0,
                "all_scores": {"O(1)": 1.0},
            }

        # ── Normalise ─────────────────────────────────────────────────
        t_norm = t / (float(t.max()) or 1.0)

        best_label = "Unknown"
        best_r2    = -np.inf
        best_slope = 0.0
        all_scores: dict[str, float] = {}

        for label, feat_fn in self.MODELS:
            try:
                # Skip O(2ⁿ) when n is large (overflow is meaningless)
                if label == "O(2ⁿ)" and float(n.max()) > 30:
                    continue

                x = feat_fn(n)
                x_norm = x / (float(np.max(np.abs(x))) or 1.0)

                if label == "O(1)":
                    y_hat = np.full_like(t_norm, float(np.mean(t_norm)))
                    r2    = self._r_squared(t_norm, y_hat)
                    slope = 0.0
                else:
                    coeffs = np.polyfit(x_norm, t_norm, 1)   # [a, b]
                    y_hat  = np.polyval(coeffs, x_norm)
                    r2     = self._r_squared(t_norm, y_hat)
                    slope  = float(coeffs[0])

                all_scores[label] = round(r2, 4)

                if r2 > best_r2:
                    best_r2    = r2
                    best_label = label
                    best_slope = slope

            except Exception:
                continue

        return {
            "complexity": best_label,
            "slope":      round(best_slope, 6),
            "r_squared":  round(best_r2, 4),
            "all_scores": all_scores,
        }