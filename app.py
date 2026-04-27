import tkinter as tk
import threading
import random
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from executor import SafeExecutor
from algorithm_project.analyzer import ComplexityAnalyzer, ModelRegistry

class AlgorithmProfilerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Algorithm Performance Evaluator")
        self.root.geometry("1200x800")
        self.root.configure(bg="#0b0c1a")
        self.executor = SafeExecutor()
        self.analyzer = ComplexityAnalyzer()
        self._setup_ui()
        self._current_canvas = None

    def _setup_ui(self):
        left = tk.Frame(self.root, bg="#11132a", width=400)
        left.pack(side="left", fill="both", expand=False, padx=10, pady=10)
        left.pack_propagate(False)
        tk.Label(left, text="Algorithm Code", font=("Arial",14,"bold"), fg="white", bg="#11132a").pack(pady=5)
        self.code_text = tk.Text(left, height=15, bg="#0b0c1a", fg="white", insertbackground="white", font=("Consolas",10))
        self.code_text.pack(padx=10, pady=5, fill="both", expand=True)
        self.code_text.insert("1.0", "# Write your function here\ndef my_function(arr):\n    return sorted(arr)")
        tk.Label(left, text="Manual Input (comma-separated)", font=("Arial",10), fg="white", bg="#11132a").pack(pady=(10,0))
        self.manual_input = tk.Entry(left, bg="#0b0c1a", fg="white")
        self.manual_input.pack(pady=5)
        self.manual_input.insert(0, "5,2,8,1,9")
        case_frame = tk.Frame(left, bg="#11132a")
        case_frame.pack(pady=10)
        tk.Label(case_frame, text="Test Case:", fg="white", bg="#11132a").pack(side="left")
        self.case_var = tk.StringVar(value="average")
        for case in ["best","average","worst"]:
            rb = tk.Radiobutton(case_frame, text=case.capitalize(), variable=self.case_var, value=case, bg="#11132a", fg="white", selectcolor="#11132a")
            rb.pack(side="left", padx=5)
        mode_frame = tk.Frame(left, bg="#11132a")
        mode_frame.pack(pady=10)
        self.mode_var = tk.StringVar(value="auto")
        tk.Radiobutton(mode_frame, text="Manual (single input)", variable=self.mode_var, value="manual", bg="#11132a", fg="white", selectcolor="#11132a").pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Auto (size sweep)", variable=self.mode_var, value="auto", bg="#11132a", fg="white", selectcolor="#11132a").pack(anchor="w")
        self.run_button = tk.Button(left, text="▶ Run Analysis", command=self.run_analysis, bg="#f59e0b", fg="black", font=("Arial",12,"bold"))
        self.run_button.pack(pady=20)
        right = tk.Frame(self.root, bg="#0f1224")
        right.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        self.result_label = tk.Label(right, text="Ready", fg="#22c55e", bg="#0f1224", font=("Arial",12), wraplength=600, justify="left")
        self.result_label.pack(pady=10)
        self.graph_frame = tk.Frame(right, bg="#0b0c1a", height=400)
        self.graph_frame.pack(fill="both", expand=True, pady=10)
        self.graph_frame.pack_propagate(False)
        tk.Label(self.graph_frame, text="Graph will appear here", fg="gray", bg="#0b0c1a").pack(expand=True)

    def run_analysis(self):
        self.run_button.config(state=tk.DISABLED, text="⏳ Running...")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            code = self.code_text.get("1.0","end").strip()
            if not code:
                self._update_result("Error: No code provided.")
                return
            if self.mode_var.get() == "manual":
                self._manual(code)
            else:
                self._auto(code)
        except Exception as e:
            self._update_result(f"Error: {e}")
        finally:
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL, text="▶ Run Analysis"))

    def _manual(self, code):
        inp = self.manual_input.get().strip()
        try:
            data = [int(x.strip()) for x in inp.split(",") if x.strip()]
        except:
            self._update_result("Invalid manual input.")
            return
        if not data:
            self._update_result("Empty input.")
            return
        elapsed, ret = self.executor.run(code, data, timeout_sec=10)
        if elapsed is None:
            self._update_result("Execution failed or timed out.")
        else:
            self._update_result(f"Size: {len(data)} | Time: {elapsed:.3f} ms | Return: {ret}")

    def _generate_test_data(self, n, case, repeats=1):
        """Return list of test arrays (for average case, generate multiple shuffles)."""
        if case == "best":
            return [list(range(n))] * repeats
        elif case == "worst":
            return [list(range(n, 0, -1))] * repeats
        else:  # average
            data_list = []
            for _ in range(repeats):
                arr = list(range(n))
                random.shuffle(arr)
                data_list.append(arr)
            return data_list

    def _auto(self, code):
        case = self.case_var.get()
        # ---- Probe for exponential ----
        probe_sizes = [5, 10, 15, 20]
        times_probe = []
        for n in probe_sizes:
            data_list = self._generate_test_data(n, case, repeats=1)
            elapsed, _ = self.executor.run(code, data_list[0], timeout_sec=8.0)
            if elapsed is None:
                self._update_result(f"Function too slow at n={n}.")
                return
            times_probe.append(elapsed)
        if len(times_probe) >= 2 and times_probe[-1] / times_probe[0] > 100:
            sizes = [5, 7, 9, 11, 13, 15, 17, 19, 20]
            self._update_result("Exponential growth detected → using small size range.")
        else:
            # Polynomial sizes: geometric progression up to 20k (safe for O(n²))
            sizes = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 20000]

        # ---- Measure with multiple shuffles for average case ----
        all_times = []
        for n in sizes:
            data_list = self._generate_test_data(n, case, repeats=3 if case == "average" else 1)
            run_times = []
            for data in data_list:
                elapsed, _ = self.executor.run(code, data, timeout_sec=8.0)
                if elapsed is not None:
                    run_times.append(elapsed)
            if run_times:
                median_time = np.median(run_times)
                all_times.append((n, median_time))
            else:
                all_times.append((n, None))
            self.root.after(0, lambda n=n: self.result_label.config(text=f"Testing size {n}..."))

        valid = [(s,t) for s,t in all_times if t is not None]
        if len(valid) < 3:
            self._update_result("Insufficient valid measurements (timeouts?). Try simpler code.")
            return
        sz, tm = zip(*valid)
        res = self.analyzer.estimate(list(sz), list(tm))
        self._show_graph(list(sz), list(tm), res["complexity"])
        self._update_result(
            f"Complexity: {res['complexity']}\n"
            f"Confidence: {res['confidence']:.2f}\n"
            f"Log‑log slope: {res['log_slope']:.3f}\n"
            f"R²: {res['r_squared']:.3f}\n"
            f"{res['interpretation']}"
        )

    def _show_graph(self, sizes, times, complexity):
        def plot():
            for w in self.graph_frame.winfo_children():
                w.destroy()
            fig, ax = plt.subplots(figsize=(6,4), dpi=100)
            fig.patch.set_facecolor("#0f1224")
            ax.set_facecolor("#0b0c1a")
            # Plot measured data
            ax.plot(sizes, times, 'o-', color='cyan', linewidth=2, label='Measured')
            # Fit and plot the winning model
            model = next((m for m in ModelRegistry.get_all() if m.name == complexity), None)
            if model:
                n_arr = np.array(sizes, dtype=float)
                f = model.feature_fn(n_arr)
                # Use least squares to avoid RankWarning
                A = np.vstack([f, np.ones_like(f)]).T
                coeffs, _, _, _ = np.linalg.lstsq(A, times, rcond=None)
                fitted = coeffs[0] * f + coeffs[1]
                ax.plot(sizes, fitted, '--', color='orange', linewidth=1.5, label=f'{model.name} fit')
            # Scale axes appropriately
            if complexity == "O(2ⁿ)":
                ax.set_yscale('log')
                ax.set_xscale('linear')
            elif complexity not in ["O(1)"]:
                ax.set_xscale('log')
                ax.set_yscale('log')
            else:
                ax.set_xscale('linear')
                ax.set_yscale('linear')
            ax.set_title(f"Time Complexity: {complexity}", color="white")
            ax.set_xlabel("Input size (n)", color="white")
            ax.set_ylabel("Time (ms)", color="white")
            ax.tick_params(colors="white")
            ax.grid(True, alpha=0.3)
            ax.legend(facecolor="#15162b", labelcolor="white")
            canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        self.root.after(0, plot)

    def _update_result(self, text):
        self.root.after(0, lambda: self.result_label.config(text=text))

if __name__ == "__main__":
    root = tk.Tk()
    app = AlgorithmProfilerApp(root)
    root.mainloop()