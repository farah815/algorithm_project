import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
import math
import warnings


@dataclass
class ComplexityModel:
    name: str
    feature_fn: callable
    is_exponential: bool = False
    order: int = 0  # for tie‑breaking


class ModelRegistry:
    """Central registry of complexity models."""
    MODELS = [
        ComplexityModel("O(1)", lambda n: np.ones_like(n), order=0),
        ComplexityModel("O(log n)", lambda n: np.log2(np.maximum(n, 2)), order=1),
        ComplexityModel("O(√n)", lambda n: np.sqrt(n), order=2),
        ComplexityModel("O(n)", lambda n: n, order=3),
        ComplexityModel("O(n log n)", lambda n: n * np.log2(np.maximum(n, 2)), order=4),
        ComplexityModel("O(n²)", lambda n: n ** 2, order=5),
        ComplexityModel("O(n² log n)", lambda n: (n ** 2) * np.log2(np.maximum(n, 2)), order=6),
        ComplexityModel("O(n³)", lambda n: n ** 3, order=7),
        ComplexityModel("O(n³ log n)", lambda n: (n ** 3) * np.log2(np.maximum(n, 2)), order=8),
        ComplexityModel("O(2ⁿ)", lambda n: 2.0 ** np.minimum(n, 20), is_exponential=True, order=9),
    ]

    @classmethod
    def get_all(cls):
        return cls.MODELS


class ComplexityAnalyzer:
    @staticmethod
    def clean_data(sizes: List[int], times: List[float]) -> Tuple[np.ndarray, np.ndarray]:
        pairs = [(float(s), float(t)) for s, t in zip(sizes, times)
                 if t is not None and np.isfinite(t) and t >= 0]
        if len(pairs) < 3:
            return np.array([]), np.array([])
        pairs.sort(key=lambda x: x[0])
        n = np.array([p[0] for p in pairs])
        t = np.array([p[1] for p in pairs])
        # Trim top 5% outliers
        if len(t) >= 5:
            cutoff = np.percentile(t, 95)
            mask = t <= cutoff
            if mask.sum() >= 3:
                n, t = n[mask], t[mask]
        return n, t

    @staticmethod
    def is_flat(n: np.ndarray, t: np.ndarray) -> Tuple[bool, str]:
        if len(t) < 3:
            return False, "Not enough points"
        # Absolute spread criterion
        if max(t) - min(t) < 0.01:
            return True, "Absolute spread < 0.01 ms"
        # Coefficient of variation
        cv = np.std(t) / (np.mean(t) + 1e-12)
        if cv < 0.10:
            return True, f"CV = {cv:.3f} < 0.10"
        # Max/min ratio
        if max(t) / (min(t) + 1e-12) < 1.5:
            return True, "Max/min ratio < 1.5"
        # All times very small
        if max(t) < 0.1:
            return True, "All times < 0.1 ms (timer noise)"
        # Fit a linear model; if slope is negligible and R² low, it's flat
        try:
            coeffs = np.polyfit(n, t, 1)
            slope = coeffs[0]
            t_pred = np.polyval(coeffs, n)
            ss_res = np.sum((t - t_pred) ** 2)
            ss_tot = np.sum((t - np.mean(t)) ** 2)
            r2 = 1 - ss_res / (ss_tot + 1e-12)
            if slope < 0.001 and r2 < 0.3:
                return True, f"Negligible slope ({slope:.5f} ms/element)"
        except:
            pass
        return False, ""

    @staticmethod
    def fit_model(n: np.ndarray, t: np.ndarray, model: ComplexityModel) -> Dict[str, Any]:
        """Return dict with r2, aic, slope."""
        try:
            if model.is_exponential:
                # Fit log(t) = a*n + b
                log_t = np.log(t + 1e-12)
                A = np.vstack([n, np.ones_like(n)]).T
                coeffs, _, _, _ = np.linalg.lstsq(A, log_t, rcond=None)
                slope, intercept = coeffs
                t_pred = np.exp(intercept + slope * n)
                ss_res = np.sum((t - t_pred) ** 2)
                ss_tot = np.sum((t - np.mean(t)) ** 2)
                r2 = 1 - ss_res / (ss_tot + 1e-12)
                return {"r2": r2, "aic": None, "slope": slope}
            else:
                f = model.feature_fn(n).astype(float)
                # Normalise to [0,1] for numerical stability
                f_norm = f / (np.max(f) or 1.0)
                t_norm = t / (np.max(t) or 1.0)
                # Use lstsq instead of polyfit to avoid RankWarning
                A = np.vstack([f_norm, np.ones_like(f_norm)]).T
                coeffs, _, _, _ = np.linalg.lstsq(A, t_norm, rcond=None)
                slope, intercept = coeffs
                t_pred = slope * f_norm + intercept
                ss_res = np.sum((t_norm - t_pred) ** 2)
                ss_tot = np.sum((t_norm - np.mean(t_norm)) ** 2)
                r2 = 1 - ss_res / (ss_tot + 1e-12)
                n_points = len(t)
                aic = n_points * np.log(ss_res / n_points) + 4 if ss_res > 0 else np.inf
                return {"r2": r2, "aic": aic, "slope": slope}
        except Exception:
            return {"r2": -np.inf, "aic": np.inf, "slope": 0.0}

    def estimate(self, sizes: List[int], times: List[float]) -> Dict[str, Any]:
        n, t = self.clean_data(sizes, times)
        if len(n) < 3:
            return {
                "complexity": "Insufficient data",
                "confidence": 0.0,
                "log_slope": 0.0,
                "r_squared": 0.0,
                "interpretation": "Need at least 3 valid data points."
            }

        # Flat time detection (O(1))
        flat, reason = self.is_flat(n, t)
        if flat:
            return {
                "complexity": "O(1)",
                "confidence": 1.0,
                "log_slope": 0.0,
                "r_squared": 1.0,
                "interpretation": f"Constant time: {reason}"
            }

        # Evaluate all models
        results = []
        for model in ModelRegistry.get_all():
            fit = self.fit_model(n, t, model)
            results.append((model, fit))

        # Filter impossible (negative slope or R² < 0)
        valid = [(m, f) for m, f in results if f["slope"] > 0 and f["r2"] > 0.2]
        if not valid:
            return {
                "complexity": "Unknown",
                "confidence": 0.0,
                "log_slope": 0.0,
                "r_squared": 0.0,
                "interpretation": "No model fits positively – high noise or wrong data."
            }

        # Exponential detection: semi‑log fit with R² > 0.95 and growth ratio > 50
        exp_models = [(m, f) for m, f in valid if m.is_exponential]
        if exp_models:
            ratio = t[-1] / (t[0] + 1e-12)
            if ratio > 50:
                best_exp = max(exp_models, key=lambda x: x[1]["r2"])
                if best_exp[1]["r2"] > 0.95:
                    return self._make_result(best_exp[0], best_exp[1], n)

        # Non‑exponential: choose by AIC (lower is better)
        non_exp = [(m, f) for m, f in valid if not m.is_exponential]
        if not non_exp:
            # fallback to exponential if any
            if exp_models:
                best = max(exp_models, key=lambda x: x[1]["r2"])
                return self._make_result(best[0], best[1], n)
            else:
                return self._make_result(valid[0][0], valid[0][1], n)

        # Filter out models with AIC = inf (perfect fit, but rare)
        aic_valid = [(m, f) for m, f in non_exp if f["aic"] is not None and np.isfinite(f["aic"])]
        if aic_valid:
            best_model, best_fit = min(aic_valid, key=lambda x: x[1]["aic"])
        else:
            # fallback to R²
            best_model, best_fit = max(non_exp, key=lambda x: x[1]["r2"])

        return self._make_result(best_model, best_fit, n)

    def _make_result(self, model: ComplexityModel, fit: Dict, n: np.ndarray) -> Dict:
        # Confidence based on R² and number of points
        confidence = min(0.99, max(0.5, fit["r2"]))
        if len(n) < 5:
            confidence *= 0.85
        confidence = round(confidence, 2)
        # Log‑log slope for polynomial models (heuristic)
        if not model.is_exponential:
            log_slope = fit["slope"] * (2.0 if "²" in model.name else 1.0)  # rough estimate
        else:
            log_slope = fit["slope"]
        return {
            "complexity": model.name,
            "confidence": confidence,
            "log_slope": round(log_slope, 3),
            "r_squared": round(fit["r2"], 3),
            "interpretation": f"{model.name} with {confidence:.0%} confidence (R²={fit['r2']:.3f})."
        }