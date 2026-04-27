from engine import Engine
from data_generator import DataGenerator
from analyzer import Analyzer

class Main:

    def __init__(self):
        self.engine = Engine()
        self.analyzer = Analyzer()

    # =========================
    # Manual Mode
    # =========================
    def run_manual(self, user_code: str, user_input: str) -> dict:

        arr = DataGenerator.from_manual(user_input)
        time = self.engine.run_code(user_code, arr)

        return {
            "mode": "Manual",
            "input_size": len(arr),
            "input_array": arr,
            "execution_time": round(time, 4)
        }

    # =========================
    # Auto Mode
    # =========================
    def run_auto(self, user_code: str, sizes: list = None):

        inputs = DataGenerator.generate_case(sizes)

        sizes_list = []
        best_times = []
        avg_times = []
        worst_times = []

        for n, cases in inputs.items():

            sizes_list.append(n)

            best_times.append(
                round(self.engine.run_code(user_code, cases["best"]), 4)
            )

            avg_times.append(
                round(self.engine.run_code(user_code, cases["average"]), 4)
            )

            worst_times.append(
                round(self.engine.run_code(user_code, cases["worst"]), 4)
            )

        result = self.analyzer.estimate(
            sizes_list,
            avg_times
        )

        return {
            "mode": "Auto",
            "sizes": sizes_list,
            "best_times": best_times,
            "avg_times": avg_times,
            "worst_times": worst_times,
            "complexity": result["complexity"],
            "slope": result["slope"]
        }


# =========================
# TEST RUN (NO GUI)
# =========================
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
    print(app.run_manual(user_code, "1,2,3,4,5"))

    print("\n========== AUTO MODE ==========")
    print(app.run_auto(
        user_code,
        [100, 500, 1000, 2000, 5000]
    ))