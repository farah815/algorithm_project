from engine import Engine
from data_generator import DataGenerator
from algorithm_project.analyzer import Analyzer


class Main:
    """
    Orchestrates manual and auto benchmarking modes.

    Now uses safe_estimate and filters None values before analysis.
    """

    def __init__(self):
        self.engine   = Engine()
        self.analyzer = Analyzer()

    # ------------------------------------------------------------------
    # Manual Mode
    # ------------------------------------------------------------------
    def run_manual(self, user_code: str, user_input: str) -> dict:
        arr = DataGenerator.from_manual(user_input)
        elapsed_ms, return_value = self.engine.run_once(user_code, arr)
        return {
            "mode":           "Manual",
            "input_size":     len(arr),
            "input_array":    arr,
            "execution_time": elapsed_ms,
            "return_value":   return_value,
        }

    # ------------------------------------------------------------------
    # Auto Mode
    # ------------------------------------------------------------------
    def run_auto(self, user_code: str, sizes: list[int] | None = None, debug: bool = False) -> dict:
        # Use safe sizes: if sizes not provided, use default (already safe)
        if sizes is None:
            sizes = DataGenerator.DEFAULT_SIZES

        # Generate input arrays for each size (best, average, worst)
        inputs = DataGenerator.generate_case(sizes=sizes)

        sizes_list:  list[int]          = []
        best_times:  list[float | None] = []
        avg_times:   list[float | None] = []
        worst_times: list[float | None] = []

        for n, cases in sorted(inputs.items()):
            sizes_list.append(n)
            best_times.append(self.engine.run_code(user_code, cases["best"]))
            avg_times.append(self.engine.run_code(user_code, cases["average"]))
            worst_times.append(self.engine.run_code(user_code, cases["worst"]))

        # Use safe_estimate for each case, filtering None values
        def _estimate(times):
            pairs = [(s, t) for s, t in zip(sizes_list, times) if t is not None]
            if len(pairs) < 3:
                return {"complexity": "Error (insufficient data)", "confidence": 0.0, "slope": 0.0, "r_squared": 0.0}
            return self.analyzer.safe_estimate([p[0] for p in pairs], [p[1] for p in pairs], debug=debug)

        best_result  = _estimate(best_times)
        avg_result   = _estimate(avg_times)
        worst_result = _estimate(worst_times)

        return {
            "mode":              "Auto",
            "sizes":             sizes_list,
            "best_times":        best_times,
            "avg_times":         avg_times,
            "worst_times":       worst_times,
            # Legacy keys (average case)
            "complexity":        avg_result.get("complexity", "Error"),
            "confidence":        avg_result.get("confidence", 0.0),
            "slope":             avg_result.get("slope", 0.0),
            "r_squared":         avg_result.get("r_squared", 0.0),
            "log_slope":         avg_result.get("log_slope", 0.0),
            # Per‑case complexities
            "best_complexity":   best_result.get("complexity", "Error"),
            "avg_complexity":    avg_result.get("complexity", "Error"),
            "worst_complexity":  worst_result.get("complexity", "Error"),
            "all_scores":        avg_result.get("scores", {}),
        }


# =============================================================================
# Standalone test (no GUI)
# =============================================================================
if __name__ == "__main__":
    app = Main()

    user_code = """
def work(arr):
    mx = arr[0]
    for i in arr:
        if i > mx:
            mx = i
    return mx
"""

    print("\n========== MANUAL MODE ==========")
    result = app.run_manual(user_code, "1,2,3,4,5")
    print(result)

    print("\n========== AUTO MODE ==========")
    result = app.run_auto(user_code, sizes=[100, 500, 1000, 2000, 5000], debug=True)
    for k, v in result.items():
        if k not in ("sizes", "best_times", "avg_times", "worst_times"):
            print(f"  {k}: {v}")