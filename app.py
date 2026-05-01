"""
Algorithm Performance Evaluator – Modern GUI with CustomTkinter
================================================================
- Dark/light theme (default dark)
- Tabbed layout (Auto / Manual / Debug)
- Shared code editor with line numbers + syntax highlighting
- All modes run in separate threads; graph rendering thread‑safe
- Exports: CSV (measurements + result) and PNG graph
"""

import csv
import math
import random
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import warnings

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from analyzer import ComplexityAnalyzer, ModelRegistry
from executor import SafeExecutor

# ----------------------------------------------------------------------
# Appearance
# ----------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Colour constants (used inside text highlights)
COLORS = {
    "keyword": "#ff79c6",
    "string":  "#50fa7b",
    "comment": "#6272a4",
    "number":  "#bd93f9",
    "bg_code": "#0b0c1a",
    "fg_code": "#e2e8f0",
}

# ----------------------------------------------------------------------
# Syntax highlighting (works on regular tkinter Text widget)
# ----------------------------------------------------------------------
KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield"
}

def highlight_syntax(text_widget):
    """Apply syntax highlighting to a tkinter Text widget."""
    for tag in text_widget.tag_names():
        text_widget.tag_delete(tag)
    text_widget.tag_config("keyword", foreground=COLORS["keyword"])
    text_widget.tag_config("string",  foreground=COLORS["string"])
    text_widget.tag_config("comment", foreground=COLORS["comment"])
    text_widget.tag_config("number",  foreground=COLORS["number"])

    content = text_widget.get("1.0", "end-1c")
    lines = content.split("\n")
    for i, line in enumerate(lines, start=1):
        # Comments
        if "#" in line:
            idx = line.index("#")
            text_widget.tag_add("comment", f"{i}.{idx}", f"{i}.end")
            line = line[:idx]
        # Simple string detection (double quotes)
        in_string = False
        start_idx = 0
        for j, ch in enumerate(line):
            if ch == '"' and (j == 0 or line[j-1] != '\\'):
                if not in_string:
                    in_string = True
                    start_idx = j
                else:
                    text_widget.tag_add("string", f"{i}.{start_idx}", f"{i}.{j+1}")
                    in_string = False
        # Keywords and numbers (rough)
        words = line.split()
        pos = 0
        for w in words:
            start = line.find(w, pos)
            end = start + len(w)
            if w in KEYWORDS:
                text_widget.tag_add("keyword", f"{i}.{start}", f"{i}.{end}")
            elif w.isdigit() or (w.replace('.','',1).isdigit() and w.count('.') <= 1):
                text_widget.tag_add("number", f"{i}.{start}", f"{i}.{end}")
            pos = end

class LineNumberedText(ctk.CTkFrame):
    """Code editor with line numbers (wraps tkinter Text)."""
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent")
        self.text = tk.Text(self, wrap="none", undo=True, font=("Consolas", 11),
                            bg=COLORS["bg_code"], fg=COLORS["fg_code"],
                            insertbackground=COLORS["fg_code"], relief="flat",
                            padx=8, pady=6, **kwargs)
        self.line_numbers = tk.Text(self, width=5, wrap="none", takefocus=0,
                                    bg="#1a1d35", fg="#94a3b8", font=("Consolas", 11),
                                    relief="flat", padx=3, pady=6)
        self.line_numbers.pack(side="left", fill="y")
        self.text.pack(side="right", fill="both", expand=True)

        self.text.bind("<KeyRelease>", self._on_change)
        self.text.bind("<MouseWheel>", self._scroll)
        self.text.bind("<Button-4>", self._scroll)
        self.text.bind("<Button-5>", self._scroll)
        self.text.bind("<Configure>", self._on_change)
        self.text.bind("<Tab>", self._tab_press)
        self.text.bind("<Control-z>", self._undo)
        self.text.bind("<Control-y>", self._redo)
        self._update_line_numbers()
        highlight_syntax(self.text)

    def _tab_press(self, event):
        self.text.insert(tk.INSERT, "    ")
        return "break"

    def _undo(self, event):
        try:
            self.text.edit_undo()
        except: pass
        return "break"

    def _redo(self, event):
        try:
            self.text.edit_redo()
        except: pass
        return "break"

    def _scroll(self, event):
        self.line_numbers.yview_scroll(int(-1*(event.delta/120)), "units")
        self.text.yview_scroll(int(-1*(event.delta/120)), "units")
        return "break"

    def _update_line_numbers(self):
        lines = self.text.get("1.0", "end-1c").count("\n") + 1
        numbers = "\n".join(str(i) for i in range(1, lines+1))
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", numbers)
        self.line_numbers.config(state="disabled")

    def _on_change(self, event=None):
        self._update_line_numbers()
        highlight_syntax(self.text)

    def get_code(self):
        return self.text.get("1.0", "end-1c")

    def set_code(self, code):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", code)
        self._on_change()

# ----------------------------------------------------------------------
# Synthetic data for debug suite
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# Main Application
# ----------------------------------------------------------------------
class AlgorithmProfilerApp(ctk.CTk):
    _POLY_SIZES  = [50, 100, 200, 400, 800, 1200, 1600, 2000]
    _EXP_SIZES   = [5, 7, 9, 11, 13, 15, 17, 19, 20]
    _PROBE_SIZES = [5, 10, 15, 20]
    _EXP_RATIO   = 100

    def __init__(self):
        super().__init__()
        self.title("Algorithm Performance Evaluator")
        self.geometry("1400x900")
        self.minsize(1200, 700)

        self.executor = SafeExecutor()
        self.analyzer = ComplexityAnalyzer()
        self._last_fig = None
        self._last_res = None
        self._last_sz = None
        self._last_tm = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        # Main container (grid)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel (code editor)
        left_frame = ctk.CTkFrame(self, width=550, corner_radius=15)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_frame.grid_propagate(False)

        ctk.CTkLabel(left_frame, text="Algorithm Code", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(15,5))
        self.code_editor = LineNumberedText(left_frame, height=25)
        self.code_editor.pack(fill="both", expand=True, padx=15, pady=10)
        self.code_editor.set_code(
            "# Write your function here\ndef my_function(arr):\n"
            "    return sorted(arr)\n"
        )

        # Right panel (tabbed views)
        right_frame = ctk.CTkFrame(self, corner_radius=15)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(0,10), pady=10)

        self.tabview = ctk.CTkTabview(right_frame, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Create tabs
        self.auto_tab = self.tabview.add("🚀 Auto Mode")
        self.manual_tab = self.tabview.add("🎛️ Manual Mode")
        self.debug_tab = self.tabview.add("🐞 Debug Mode")

        self._build_auto_tab()
        self._build_manual_tab()
        self._build_debug_tab()

    # ------------------------------------------------------------------
    # Auto Tab
    # ------------------------------------------------------------------
    def _build_auto_tab(self):
        # Top controls
        ctrl_frame = ctk.CTkFrame(self.auto_tab, fg_color="transparent")
        ctrl_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(ctrl_frame, text="Test case:").pack(side="left", padx=(0,10))
        self.case_var = ctk.StringVar(value="average")
        for val, col in [("best", "#22c55e"), ("average", "#3b82f6"), ("worst", "#ef4444")]:
            rb = ctk.CTkRadioButton(ctrl_frame, text=val.capitalize(),
                                    variable=self.case_var, value=val,
                                    fg_color=col, hover_color=col)
            rb.pack(side="left", padx=5)

        self.auto_run_btn = ctk.CTkButton(ctrl_frame, text="▶ Run Auto Analysis",
                                          command=self._run_auto, fg_color="#f59e0b",
                                          text_color="black", font=ctk.CTkFont(size=13, weight="bold"))
        self.auto_run_btn.pack(side="right", padx=10)

        # Status + result
        self.auto_status = ctk.CTkLabel(self.auto_tab, text="Ready", text_color="#22c55e", anchor="w")
        self.auto_status.pack(fill="x", padx=15, pady=5)

        # Graph frame
        self.auto_graph_frame = ctk.CTkFrame(self.auto_tab, fg_color="#0b0c1a", corner_radius=10)
        self.auto_graph_frame.pack(fill="both", expand=True, padx=15, pady=10)
        self.auto_graph_label = ctk.CTkLabel(self.auto_graph_frame, text="Graph will appear here")
        self.auto_graph_label.pack(expand=True)

        # Export buttons
        exp_frame = ctk.CTkFrame(self.auto_tab, fg_color="transparent")
        exp_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(exp_frame, text="💾 Export CSV", command=self._export_csv,
                      fg_color="#2d2f4a", width=120).pack(side="left", padx=5)
        ctk.CTkButton(exp_frame, text="🖼 Save Graph", command=self._export_graph,
                      fg_color="#2d2f4a", width=120).pack(side="left", padx=5)

    # ------------------------------------------------------------------
    # Manual Tab
    # ------------------------------------------------------------------
    def _build_manual_tab(self):
        # Fixed array input
        fixed_frame = ctk.CTkFrame(self.manual_tab, corner_radius=10)
        fixed_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(fixed_frame, text="Fixed Array (single run)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,0))
        ctk.CTkLabel(fixed_frame, text="Comma-separated integers:").pack(anchor="w", padx=10)
        self.manual_array_entry = ctk.CTkEntry(fixed_frame, placeholder_text="5,2,8,1,9")
        self.manual_array_entry.pack(fill="x", padx=10, pady=5)
        self.manual_array_entry.insert(0, "5,2,8,1,9")
        self.manual_run_btn = ctk.CTkButton(fixed_frame, text="Run on this array", command=self._run_manual_fixed,
                                            fg_color="#f59e0b", text_color="black")
        self.manual_run_btn.pack(pady=10)

        # Custom sizes sweep
        sweep_frame = ctk.CTkFrame(self.manual_tab, corner_radius=10)
        sweep_frame.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(sweep_frame, text="Custom Sizes Sweep", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,0))
        ctk.CTkLabel(sweep_frame, text="Sizes (comma-separated):").pack(anchor="w", padx=10)
        self.manual_sizes_entry = ctk.CTkEntry(sweep_frame, placeholder_text="100,200,400,800,1600")
        self.manual_sizes_entry.pack(fill="x", padx=10, pady=5)
        self.manual_sizes_entry.insert(0, "100,200,400,800,1600")
        ctk.CTkLabel(sweep_frame, text="Runs per size (1-20):").pack(anchor="w", padx=10)
        self.manual_runs_scale = ctk.CTkSlider(sweep_frame, from_=1, to=20, number_of_steps=19)
        self.manual_runs_scale.set(10)
        self.manual_runs_scale.pack(fill="x", padx=10, pady=5)
        self.manual_sweep_btn = ctk.CTkButton(sweep_frame, text="Run size sweep", command=self._run_manual_sweep,
                                              fg_color="#f59e0b", text_color="black")
        self.manual_sweep_btn.pack(pady=10)

        # Status + graph
        self.manual_status = ctk.CTkLabel(self.manual_tab, text="Ready", text_color="#22c55e")
        self.manual_status.pack(fill="x", padx=15, pady=5)
        self.manual_graph_frame = ctk.CTkFrame(self.manual_tab, fg_color="#0b0c1a", corner_radius=10)
        self.manual_graph_frame.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkLabel(self.manual_graph_frame, text="Graph will appear here").pack(expand=True)

    # ------------------------------------------------------------------
    # Debug Tab
    # ------------------------------------------------------------------
    def _build_debug_tab(self):
        self.debug_btn = ctk.CTkButton(self.debug_tab, text="▶ Run Debug Suite", command=self._run_debug,
                                       fg_color="#f59e0b", text_color="black", font=ctk.CTkFont(size=14, weight="bold"))
        self.debug_btn.pack(pady=15)

        self.debug_text = ctk.CTkTextbox(self.debug_tab, font=ctk.CTkFont(family="Consolas", size=11),
                                         wrap="word")
        self.debug_text.pack(fill="both", expand=True, padx=15, pady=10)

    # ------------------------------------------------------------------
    # Auto Mode Logic
    # ------------------------------------------------------------------
    def _run_auto(self):
        self.auto_run_btn.configure(state="disabled", text="⏳ Running...")
        self._update_auto("Initialising...")
        threading.Thread(target=self._auto_worker, daemon=True).start()

    def _auto_worker(self):
        try:
            code = self.code_editor.get_code()
            if not code:
                self._update_auto("Error: empty code")
                return
            case = self.case_var.get()
            self._update_auto("Probing growth rate...")
            probe_times = self.executor.probe_growth(code, self._PROBE_SIZES, timeout_sec=30)
            valid_p = [t for t in probe_times if t is not None and t > 0]
            is_exp = len(valid_p) >= 2 and valid_p[-1] / valid_p[0] > self._EXP_RATIO
            sizes = self._EXP_SIZES if is_exp else self._POLY_SIZES
            if is_exp:
                self._update_auto("Exponential growth detected → small n range")
            measured = []
            for n in sizes:
                self._update_auto(f"Benchmarking n = {n}...")
                data = self._make_data(n, case)
                elapsed, _ = self.executor.run(code, data, timeout_sec=10)
                measured.append((n, elapsed))
            valid = [(s, t) for s, t in measured if t is not None]
            if len(valid) < 3:
                self._update_auto("Too few valid measurements (timeouts?)")
                return
            sz, tm = zip(*valid)
            sz, tm = list(sz), list(tm)
            res = self.analyzer.estimate(sz, tm)
            self._last_res, self._last_sz, self._last_tm = res, sz, tm
            self._draw_graph(self.auto_graph_frame, sz, tm, res)
            self._update_auto(
                f"Complexity: {res['complexity']}\nConfidence: {res['confidence']:.2f}\n"
                f"Log‑log slope: {res['log_slope']:.4f}\nR²: {res['r_squared']:.4f}\n\n{res['interpretation']}"
            )
        except Exception as e:
            self._update_auto(f"Error: {e}")
        finally:
            self.auto_run_btn.configure(state="normal", text="▶ Run Auto Analysis")

    def _update_auto(self, text):
        self.auto_status.configure(text=text)

    # ------------------------------------------------------------------
    # Manual Mode
    # ------------------------------------------------------------------
    def _run_manual_fixed(self):
        self.manual_run_btn.configure(state="disabled")
        threading.Thread(target=self._manual_fixed_worker, daemon=True).start()

    def _manual_fixed_worker(self):
        try:
            code = self.code_editor.get_code()
            raw = self.manual_array_entry.get().strip()
            data = [int(x.strip()) for x in raw.split(",") if x.strip()]
            if not data:
                self._update_manual("Empty input")
                return
            elapsed, ret = self.executor.run(code, data, timeout_sec=10)
            if elapsed is None:
                self._update_manual("Execution failed or timed out")
            else:
                self._update_manual(f"Size: {len(data)} | Time: {elapsed:.4f} ms | Return: {ret}")
        except Exception as e:
            self._update_manual(f"Error: {e}")
        finally:
            self.manual_run_btn.configure(state="normal")

    def _run_manual_sweep(self):
        self.manual_sweep_btn.configure(state="disabled")
        threading.Thread(target=self._manual_sweep_worker, daemon=True).start()

    def _manual_sweep_worker(self):
        try:
            code = self.code_editor.get_code()
            sizes_str = self.manual_sizes_entry.get().strip()
            sizes = [int(x.strip()) for x in sizes_str.split(",") if x.strip()]
            runs = int(self.manual_runs_scale.get())
            times = []
            for n in sizes:
                self._update_manual(f"Benchmarking n = {n}...")
                data = self._make_data(n, "average")
                elapsed, _ = self.executor.run(code, data, timeout_sec=10, runs=runs)
                times.append(elapsed)
            res = self.analyzer.estimate(sizes, times)
            self._draw_graph(self.manual_graph_frame, sizes, times, res)
            self._update_manual(f"Complexity: {res['complexity']} (R²={res['r_squared']:.3f})")
        except Exception as e:
            self._update_manual(f"Error: {e}")
        finally:
            self.manual_sweep_btn.configure(state="normal")

    def _update_manual(self, text):
        self.manual_status.configure(text=text)

    # ------------------------------------------------------------------
    # Debug Mode
    # ------------------------------------------------------------------
    def _run_debug(self):
        self.debug_btn.configure(state="disabled")
        threading.Thread(target=self._debug_worker, daemon=True).start()

    def _debug_worker(self):
        self.debug_text.delete("0.0", "end")
        lines = []
        lines.append(f"{'Expected':<14} {'Detected':<14} {'Conf':>5} {'R²':>7} {'Slope':>9}  OK")
        lines.append("-"*62)
        passed = 0
        for true_label, (sizes, times) in DEBUG_SUITE.items():
            res = self.analyzer.estimate(sizes, times)
            ok = "✓" if res["complexity"] == true_label else "✗"
            if ok == "✓":
                passed += 1
            lines.append(
                f"{true_label:<14} {res['complexity']:<14} "
                f"{res['confidence']:>5.2f} {res['r_squared']:>7.4f} "
                f"{res['log_slope']:>9.4f}  {ok}"
            )
        lines.append("-"*62)
        lines.append(f"Result: {passed}/{len(DEBUG_SUITE)} correct")
        self.debug_text.insert("0.0", "\n".join(lines))
        self.debug_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Graph Drawing
    # ------------------------------------------------------------------
    def _draw_graph(self, parent, sizes, times, res):
        complexity = res["complexity"]
        def plot():
            # Clear previous graph
            for w in parent.winfo_children():
                w.destroy()
            fig, ax = plt.subplots(figsize=(6.8, 4.4), dpi=100)
            fig.patch.set_facecolor("#0f1224")
            ax.set_facecolor("#0b0c1a")
            ax.plot(sizes, times, "o-", color="#22d3ee", lw=2, ms=5, label="Measured", zorder=3)
            model = ModelRegistry.get(complexity)
            if model:
                try:
                    n_arr = np.array(sizes, dtype=float)
                    t_arr = np.array(times, dtype=float)
                    if model.is_exponential:
                        logt = np.log(t_arr + 1e-12)
                        A = np.vstack([n_arr, np.ones_like(n_arr)]).T
                        c, _, _, _ = np.linalg.lstsq(A, logt, rcond=None)
                        fitted = np.exp(c[0] * n_arr + c[1])
                    else:
                        f = model.feature_fn(n_arr).astype(float)
                        if np.all(np.isfinite(f)):
                            A = np.vstack([f, np.ones_like(f)]).T
                            c, _, _, _ = np.linalg.lstsq(A, t_arr, rcond=None)
                            fitted = c[0] * f + c[1]
                        else:
                            fitted = None
                    if fitted is not None:
                        ax.plot(sizes, fitted, "--", color="#f59e0b", lw=1.8, label=f"{complexity} fit", zorder=2)
                except: pass
            # Axis scaling
            if complexity == "O(1)":
                ax.set_xscale("linear"); ax.set_yscale("linear")
            elif complexity == "O(2ⁿ)":
                ax.set_xscale("linear"); ax.set_yscale("log")
            else:
                ax.set_xscale("log"); ax.set_yscale("log")
            ax.set_title(f"Time Complexity: {complexity}", color="white")
            ax.set_xlabel("Input size (n)", color="#94a3b8")
            ax.set_ylabel("Time (ms)", color="#94a3b8")
            ax.tick_params(colors="#94a3b8")
            for spine in ax.spines.values():
                spine.set_edgecolor("#2d3050")
            ax.grid(True, alpha=0.2, linestyle="--", color="#2d3050")
            ax.legend(facecolor="#1e2245", labelcolor="white", edgecolor="#2d3050")
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self._last_fig = fig
        self.after(0, plot)

    # ------------------------------------------------------------------
    # Helpers & Export
    # ------------------------------------------------------------------
    @staticmethod
    def _make_data(n, case):
        if case == "best":
            return list(range(n))
        if case == "worst":
            return list(range(n, 0, -1))
        arr = list(range(n))
        random.shuffle(arr)
        return arr

    def _export_csv(self):
        if self._last_sz is None:
            messagebox.showinfo("Export", "Run an Auto analysis first")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        res = self._last_res or {}
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["complexity", "confidence", "log_slope", "r_squared"])
            w.writerow([res.get("complexity",""), res.get("confidence",""),
                        res.get("log_slope",""), res.get("r_squared","")])
            w.writerow([])
            w.writerow(["input_size", "time_ms"])
            for s, t in zip(self._last_sz, self._last_tm):
                w.writerow([s, t])
        messagebox.showinfo("Export", f"Saved to {path}")

    def _export_graph(self):
        if self._last_fig is None:
            messagebox.showinfo("Export", "Run an Auto analysis first")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")])
        if not path:
            return
        self._last_fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=self._last_fig.get_facecolor())
        messagebox.showinfo("Export", f"Saved to {path}")

# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = AlgorithmProfilerApp()
    app.mainloop()
