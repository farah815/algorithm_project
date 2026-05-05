"""
main_page.py
============
Main application UI – code editor, tabs, workers, graph, exports.
Keyboard shortcuts are unbound when the page is destroyed.
"""

import csv
import threading
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import warnings
from datetime import datetime

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from analyzer import ComplexityAnalyzer, ModelRegistry
from executor import SafeExecutor
from data_generator import make_data, parse_manual_input
from gui_components import LineNumberedText

from constants import (BG, PANEL, BORDER, ACCENT, ACCENT2, ACCENT3, ACCENT4,
                       TEXT, MUTED, GREEN, RED, ALGORITHM_EXAMPLES)


class MainPage(tk.Frame):
    """Main tool page with code editor, test case selector, tabs & graph."""

    _POLY_SIZES  = [50, 100, 200, 400, 800, 1200, 1600, 2000]
    _EXP_SIZES   = [5, 7, 9, 11, 13, 15, 17, 19, 20]
    _PROBE_SIZES = [5, 10, 15, 20]
    _EXP_RATIO   = 100

    def __init__(self, master, switch_to_start):
        super().__init__(master, bg=BG)
        self.master = master
        self.switch_to_start = switch_to_start

        self.executor = SafeExecutor()
        self.analyzer = ComplexityAnalyzer()

        self._last_fig = None
        self._last_res = None
        self._last_sz  = None
        self._last_tm  = None

        self._build_ui()
        self._setup_keyboard_shortcuts()

    # ── Keyboard shortcuts ──────────────────────────────────────────

    def _on_enter(self, event):
        current = self.tabs.get()
        if current == "Auto Analysis":
            self._run_auto()
        elif current == "Manual Benchmarks":
            self._run_manual_sweep()

    def _setup_keyboard_shortcuts(self):
        self.master.bind("<Control-Return>", lambda _: self._run_auto())
        self.master.bind("<Return>", self._on_enter)

    def _unbind_shortcuts(self):
        self.master.unbind("<Control-Return>")
        self.master.unbind("<Return>")

    # ── UI construction ─────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel
        left = ctk.CTkFrame(self, width=500, corner_radius=14,
                            fg_color=PANEL, border_color=BORDER, border_width=1)
        left.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left.grid_propagate(False)

        # Header
        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(14, 4))
        ctk.CTkButton(hdr, text="← Back", width=80, height=28,
                      fg_color=ACCENT, hover_color=ACCENT2,
                      text_color="white", font=ctk.CTkFont(size=12),
                      command=self.switch_to_start).pack(side="left")
        ctk.CTkLabel(hdr, text="Algorithm Code",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=TEXT).pack(side="left", padx=14)

        # Example dropdown
        example_frame = ctk.CTkFrame(left, fg_color="transparent")
        example_frame.pack(fill="x", padx=14, pady=(0, 4))

        ctk.CTkLabel(example_frame, text="Examples:", text_color=ACCENT3,
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 8))

        self.example_var = ctk.StringVar(value="Select an example...")
        self.example_menu = ctk.CTkComboBox(
            example_frame,
            variable=self.example_var,
            values=list(ALGORITHM_EXAMPLES.keys()),
            command=self._on_example_selected,
            fg_color=BG,
            border_color=BORDER,
            button_color=ACCENT,
            button_hover_color=ACCENT2,
            dropdown_fg_color=PANEL,
            dropdown_text_color=TEXT,
            text_color=TEXT,
            font=ctk.CTkFont(size=11),
            width=250,
        )
        self.example_menu.pack(side="left", pady=2)

        # Code editor
        self.code_editor = LineNumberedText(left, height=24)
        self.code_editor.pack(fill="both", expand=True, padx=14, pady=(4, 8))
        self.code_editor.set_code(ALGORITHM_EXAMPLES["Select an example..."])

        self._code_cleared = False
        def _clear(_=None):
            if not self._code_cleared:
                self.code_editor.set_code("")
                self._code_cleared = True

        self.code_editor.text.bind("<FocusIn>", _clear)
        self.code_editor.text.bind("<Key>", _clear)

        # Test case selector
        setup = ctk.CTkFrame(left, fg_color="transparent")
        setup.pack(fill="x", padx=14, pady=(0, 8))
        ctk.CTkLabel(setup, text="Test case:", text_color=TEXT).pack(side="left", padx=(0, 8))
        self.case_var = ctk.StringVar(value="average")
        for val, col in [("best", GREEN), ("average", "#3b82f6"), ("worst", RED)]:
            ctk.CTkRadioButton(setup, text=val.capitalize(),
                               variable=self.case_var, value=val,
                               fg_color=col, hover_color=col,
                               text_color=TEXT).pack(side="left", padx=4)
        self.auto_btn = ctk.CTkButton(
            setup, text="▶ Run Auto  [Ctrl+Enter]",
            command=self._run_auto,
            fg_color=ACCENT, hover_color=ACCENT2,
            text_color="white", font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.auto_btn.pack(side="right", padx=4)

        # Right panel (tabs)
        right = ctk.CTkFrame(self, corner_radius=14,
                             fg_color=PANEL, border_color=BORDER, border_width=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)

        self.tabs = ctk.CTkTabview(
            right, corner_radius=10, fg_color=PANEL,
            segmented_button_fg_color=BG,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT2,
            segmented_button_unselected_color=PANEL,
            segmented_button_unselected_hover_color=MUTED,
            text_color=TEXT,
        )
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_auto_tab(self.tabs.add("Auto Analysis"))
        self._build_manual_tab(self.tabs.add("Manual Benchmarks"))

    def _on_example_selected(self, choice):
        code = ALGORITHM_EXAMPLES.get(choice, ALGORITHM_EXAMPLES["Select an example..."])
        self.code_editor.set_code(code)
        self._code_cleared = True   # prevent clearing on first click

    # ── Auto Tab ──────────────────────────────────────────────────────

    def _build_auto_tab(self, tab):
        self.auto_status = ctk.CTkLabel(
            tab, text="Ready — pick an example or type your own function, then press ▶",
            text_color=ACCENT3, anchor="w", wraplength=700,
        )
        self.auto_status.pack(fill="x", padx=14, pady=4)

        self.auto_progress = ctk.CTkProgressBar(tab, mode="indeterminate",
                                                 progress_color=ACCENT,
                                                 fg_color=MUTED)

        self.auto_graph = ctk.CTkFrame(tab, fg_color=BG,
                                        border_color=BORDER, border_width=1,
                                        corner_radius=10)
        self.auto_graph.pack(fill="both", expand=True, padx=14, pady=(4, 6))
        ctk.CTkLabel(self.auto_graph, text="Graph will appear here",
                     text_color=ACCENT3).pack(expand=True)

        exp = ctk.CTkFrame(tab, fg_color="transparent")
        exp.pack(fill="x", padx=14, pady=(0, 10))
        ctk.CTkButton(exp, text="💾 Export CSV", command=self._export_csv,
                      fg_color=MUTED, hover_color=BORDER,
                      text_color=TEXT, width=130).pack(side="left", padx=(0, 6))
        ctk.CTkButton(exp, text="🖼 Save Graph", command=self._export_graph,
                      fg_color=MUTED, hover_color=BORDER,
                      text_color=TEXT, width=130).pack(side="left")

    # ── Manual Tab ────────────────────────────────────────────────────

    def _build_manual_tab(self, tab):
        # Fixed array
        sec1 = ctk.CTkFrame(tab, corner_radius=10, fg_color=PANEL,
                             border_color=BORDER, border_width=1)
        sec1.pack(fill="x", padx=14, pady=(10, 6))
        ctk.CTkLabel(sec1, text="Fixed Array (single run)",
                     font=ctk.CTkFont(weight="bold"), text_color=TEXT).pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(sec1, text="Comma-separated integers:",
                     text_color=ACCENT3).pack(anchor="w", padx=10)
        self.m_array = ctk.CTkEntry(sec1, placeholder_text="5,2,8,1,9",
                                     fg_color=BG, border_color=ACCENT, text_color=TEXT)
        self.m_array.pack(fill="x", padx=10, pady=4)
        self.m_array.insert(0, "5,2,8,1,9")
        self.m_fixed_btn = ctk.CTkButton(
            sec1, text="▶ Run on this array",
            command=self._run_manual_fixed,
            fg_color=ACCENT, hover_color=ACCENT2, text_color="white",
        )
        self.m_fixed_btn.pack(pady=(4, 10))
        self.m_array.bind("<Return>", lambda _: self._run_manual_fixed())

        # Size sweep
        sec2 = ctk.CTkFrame(tab, corner_radius=10, fg_color=PANEL,
                             border_color=BORDER, border_width=1)
        sec2.pack(fill="x", padx=14, pady=6)
        ctk.CTkLabel(sec2, text="Custom Sizes Sweep",
                     font=ctk.CTkFont(weight="bold"), text_color=TEXT).pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(sec2, text="Sizes (comma-separated):",
                     text_color=ACCENT3).pack(anchor="w", padx=10)
        self.m_sizes = ctk.CTkEntry(sec2, placeholder_text="100,200,400,800,1600",
                                     fg_color=BG, border_color=ACCENT, text_color=TEXT)
        self.m_sizes.pack(fill="x", padx=10, pady=4)
        self.m_sizes.insert(0, "100,200,400,800,1600")

        runs_row = ctk.CTkFrame(sec2, fg_color="transparent"); runs_row.pack(fill="x", padx=10)
        ctk.CTkLabel(runs_row, text="Runs per size:", text_color=ACCENT3).pack(side="left")
        self.m_runs = ctk.CTkSlider(runs_row, from_=1, to=20, number_of_steps=19,
                                     button_color=ACCENT, button_hover_color=ACCENT2,
                                     progress_color=BORDER, width=180)
        self.m_runs.set(7); self.m_runs.pack(side="left", padx=8)
        self.m_runs_lbl = ctk.CTkLabel(runs_row, text="7", text_color=TEXT, width=24)
        self.m_runs_lbl.pack(side="left")
        self.m_runs.configure(command=lambda v: self.m_runs_lbl.configure(text=str(int(v))))

        self.m_sweep_btn = ctk.CTkButton(
            sec2, text="▶ Run Sweep",
            command=self._run_manual_sweep,
            fg_color=ACCENT, hover_color=ACCENT2, text_color="white",
        )
        self.m_sweep_btn.pack(pady=(4, 10))

        self.m_status = ctk.CTkLabel(tab, text="Ready", text_color=ACCENT3,
                                      anchor="w", wraplength=700)
        self.m_status.pack(fill="x", padx=14, pady=4)

        self.m_graph = ctk.CTkFrame(tab, fg_color=BG, border_color=BORDER,
                                     border_width=1, corner_radius=10)
        self.m_graph.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        ctk.CTkLabel(self.m_graph, text="Graph will appear here",
                     text_color=ACCENT3).pack(expand=True)

    # ══════════════════════════════════════════════════════════════════
    # WORKERS
    # ══════════════════════════════════════════════════════════════════

    def _run_auto(self):
        self.auto_btn.configure(state="disabled", text="⏳ Running…")
        self.auto_progress.pack(fill="x", padx=14, pady=(0, 4))
        self.auto_progress.start()
        threading.Thread(target=self._auto_worker, daemon=True).start()

    def _auto_worker(self):
        start_time = None
        def done():
            self.after(0, lambda: self.auto_btn.configure(state="normal", text="▶ Run Auto  [Ctrl+Enter]"))
            self.after(0, self.auto_progress.stop)
            self.after(0, self.auto_progress.pack_forget)

        try:
            import time
            start_time = time.perf_counter()
            code = self.code_editor.get_code().strip()
            if not code:
                self._set(self.auto_status, "Error: no code entered.")
                self.after(0, done); return

            case = self.case_var.get()

            self._set(self.auto_status, "Probing growth rate…")
            probe_times, stderr = self.executor.probe_growth(code, self._PROBE_SIZES, timeout_sec=30)
            if stderr:
                self._set(self.auto_status, "Error:\n" + stderr.splitlines()[-1])
                self.after(0, done); return

            valid_p = [t for t in probe_times if t is not None and t > 0]
            is_exp  = len(valid_p) >= 2 and valid_p[-1] / valid_p[0] > self._EXP_RATIO
            sizes   = self._EXP_SIZES if is_exp else self._POLY_SIZES

            if is_exp:
                self._set(self.auto_status, "Exponential growth detected → small n range")

            measured = []
            for n in sizes:
                self._set(self.auto_status, f"Benchmarking n = {n}…")
                elapsed, _, stderr = self.executor.run(code, make_data(n, case), timeout_sec=10)
                if stderr:
                    self._set(self.auto_status, "Error:\n" + stderr.splitlines()[-1])
                    self.after(0, done); return
                measured.append((n, elapsed))

            valid = [(s, t) for s, t in measured if t is not None and t > 0]
            if len(valid) < 3:
                self._set(self.auto_status,
                    "⚠ Too few valid measurements (<3). Check for timeouts or errors.")
                self._show_warning_in_graph(
                    "⚠ Too few valid measurements.\nThe function may be timing out or crashing.\n"
                    "Try a simpler algorithm or reduce input sizes."
                )
                self.after(0, done); return

            sz, tm = zip(*valid); sz, tm = list(sz), list(tm)
            res = self.analyzer.estimate(sz, tm)
            self._last_res, self._last_sz, self._last_tm = res, sz, tm

            if min(tm) <= 0:
                tm = [max(1e-12, t) for t in tm]

            self._draw_graph(self.auto_graph, sz, tm, res)

            total = time.perf_counter() - start_time if start_time else 0
            self._set(self.auto_status,
                f"Complexity: {res['complexity']}  │  Conf: {res['confidence']:.2f}  │  "
                f"Slope: {res['log_slope']:.4f}  │  R² = {res['r_squared']:.4f}  │  Done in {total:.2f}s\n"
                f"{res['interpretation']}"
            )
        except Exception as exc:
            self._set(self.auto_status, f"Error: {exc}")
        finally:
            self.after(0, done)

    def _show_warning_in_graph(self, text):
        for w in self.auto_graph.winfo_children(): w.destroy()
        ctk.CTkLabel(self.auto_graph, text=text,
                     text_color="#fbbf24", wraplength=500,
                     font=ctk.CTkFont(size=12)).pack(expand=True)

    def _run_manual_fixed(self):
        self.m_fixed_btn.configure(state="disabled")
        threading.Thread(target=self._manual_fixed_worker, daemon=True).start()

    def _manual_fixed_worker(self):
        try:
            code = self.code_editor.get_code().strip()
            data = parse_manual_input(self.m_array.get())
            elapsed, ret, stderr = self.executor.run(code, data, timeout_sec=10)
            if stderr:
                self._set(self.m_status, "Error:\n" + stderr)
            elif elapsed is None:
                self._set(self.m_status, "⚠ Execution failed or timed out.")
            else:
                self._set(self.m_status,
                    f"Size: {len(data)}  │  Time: {elapsed:.4f} ms  │  Return: {ret}")
        except ValueError as exc:
            self._set(self.m_status, f"Input error: {exc}")
        except Exception as exc:
            self._set(self.m_status, f"Error: {exc}")
        finally:
            self.after(0, lambda: self.m_fixed_btn.configure(state="normal"))

    def _run_manual_sweep(self):
        self.m_sweep_btn.configure(state="disabled")
        threading.Thread(target=self._manual_sweep_worker, daemon=True).start()

    def _manual_sweep_worker(self):
        try:
            code  = self.code_editor.get_code().strip()
            sizes = [int(x.strip()) for x in self.m_sizes.get().split(",") if x.strip()]
            runs  = int(self.m_runs.get())
            times = []
            for n in sizes:
                self._set(self.m_status, f"Benchmarking n = {n}…")
                elapsed, _, stderr = self.executor.run(code, make_data(n, "average"),
                                                       timeout_sec=10, runs=runs)
                if stderr:
                    self._set(self.m_status, "Error:\n" + stderr)
                    return
                times.append(elapsed)
            res = self.analyzer.estimate(sizes, times)
            self._draw_graph(self.m_graph, sizes, times, res)
            self._set(self.m_status,
                f"Complexity: {res['complexity']}  │  R² = {res['r_squared']:.4f}  │  Confidence: {res['confidence']:.2f}")
        except Exception as exc:
            self._set(self.m_status, f"Error: {exc}")
        finally:
            self.after(0, lambda: self.m_sweep_btn.configure(state="normal"))

    # ══════════════════════════════════════════════════════════════════
    # GRAPH RENDERING
    # ══════════════════════════════════════════════════════════════════

    def _draw_graph(self, parent, sizes, times, res):
        complexity = res["complexity"]
        clean_times = [t for t in times if t is not None and t > 0]
        clean_sizes = [s for s, t in zip(sizes, times) if t is not None and t > 0]

        def plot():
            for w in parent.winfo_children(): w.destroy()
            if not clean_times or len(clean_times) < 3:
                ctk.CTkLabel(parent, text="Not enough valid data to plot.",
                             text_color=ACCENT3).pack(expand=True)
                return

            fig, ax = plt.subplots(figsize=(6.8, 4.2), dpi=100)
            fig.patch.set_facecolor(PANEL); ax.set_facecolor(BG)
            n_arr, t_arr = np.array(clean_sizes), np.array(clean_times)

            ax.plot(clean_sizes, clean_times, "o-", color=ACCENT3, lw=2, ms=5,
                    label="Measured", zorder=3)

            model = ModelRegistry.get(complexity)
            if model and len(n_arr) >= 3:
                try:
                    if model.is_exponential:
                        log_t = np.log(t_arr + 1e-12)
                        A = np.vstack([n_arr, np.ones_like(n_arr)]).T
                        with warnings.catch_warnings(): warnings.filterwarnings("ignore")
                        c, *_ = np.linalg.lstsq(A, log_t, rcond=None)
                        fitted = np.exp(c[0] * n_arr + c[1])
                    else:
                        f = model.feature_fn(n_arr).astype(float)
                        if np.all(np.isfinite(f)):
                            A = np.vstack([f, np.ones_like(f)]).T
                            with warnings.catch_warnings(): warnings.filterwarnings("ignore")
                            c, *_ = np.linalg.lstsq(A, t_arr, rcond=None)
                            fitted = c[0] * f + c[1]
                        else: fitted = None
                    if fitted is not None and np.all(np.isfinite(fitted)):
                        ax.plot(clean_sizes, fitted, "--", color=ACCENT4, lw=1.8,
                                label=f"{complexity} fit", zorder=2)
                except Exception: pass

            if complexity == "O(2ⁿ)":
                ax.set_xscale("linear"); ax.set_yscale("log")
            elif complexity == "O(1)":
                ax.set_xscale("linear"); ax.set_yscale("linear")
            else:
                if min(clean_times) <= 0 or min(clean_sizes) <= 0:
                    ax.set_xscale("linear"); ax.set_yscale("linear")
                else:
                    ax.set_xscale("log"); ax.set_yscale("log")

            ax.set_title(f"Time Complexity: {complexity}", color="white",
                         fontsize=14, fontweight="bold", pad=10)
            ax.set_xlabel("Input size (n)", color=ACCENT3, fontsize=12)
            ax.set_ylabel("Time (ms)", color=ACCENT3, fontsize=12)
            ax.tick_params(colors="#bfc9ff", labelsize=10)
            for spine in ax.spines.values(): spine.set_edgecolor(BORDER)
            ax.grid(True, alpha=0.35, linestyle="--", color=BORDER)
            ax.legend(loc='upper left', fontsize=10,
                      facecolor=PANEL, edgecolor=BORDER, labelcolor="white")

            try:
                fig.tight_layout(pad=1.2)
            except ValueError:
                pass

            cv = FigureCanvasTkAgg(fig, master=parent)
            cv.draw()
            cv.get_tk_widget().pack(fill="both", expand=True)
            self._last_fig = fig

        self.after(0, plot)

    # ── Export ────────────────────────────────────────────────────────

    def _export_csv(self):
        if self._last_sz is None:
            mb.showinfo("Export CSV", "Run an Auto analysis first."); return
        path = fd.asksaveasfilename(defaultextension=".csv",
                                    filetypes=[("CSV", "*.csv")],
                                    initialfile=f"complexity_{datetime.now():%Y%m%d_%H%M%S}.csv")
        if not path: return
        res = self._last_res or {}
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["complexity", "confidence", "log_slope", "r_squared"])
            w.writerow([res.get("complexity",""), res.get("confidence",""),
                        res.get("log_slope",""), res.get("r_squared","")])
            w.writerow([]); w.writerow(["input_size", "time_ms"])
            for s, t in zip(self._last_sz, self._last_tm):
                w.writerow([s, t])
        mb.showinfo("Export CSV", f"Saved:\n{path}")

    def _export_graph(self):
        if self._last_fig is None:
            mb.showinfo("Save Graph", "Run an Auto analysis first."); return
        path = fd.asksaveasfilename(defaultextension=".png",
                                    filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")],
                                    initialfile=f"graph_{datetime.now():%Y%m%d_%H%M%S}.png")
        if not path: return
        self._last_fig.savefig(path, dpi=150, bbox_inches="tight",
                               facecolor=self._last_fig.get_facecolor())
        mb.showinfo("Save Graph", f"Saved:\n{path}")

    def _set(self, widget, text: str) -> None:
        self.after(0, lambda: widget.configure(text=text))

    # ── Cleanup on page switch ───────────────────────────────────────

    def destroy(self):
        self._unbind_shortcuts()
        super().destroy()