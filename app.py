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
from data_generator import make_data
from gui_components import LineNumberedText, highlight_syntax, COLORS

# ----------------------------------------------------------------------
# Appearance
# ----------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Shared color palette ───────────────────────────────────────────────
BG      = "#07080f"
PANEL   = "#0d0e1f"
BORDER  = "#3730a3"
ACCENT  = "#7c3aed"
ACCENT2 = "#6d28d9"
ACCENT3 = "#a78bfa"
ACCENT4 = "#e879f9"
TEXT    = "#e2e8f0"
MUTED   = "#1e1b4b"


class AlgorithmProfilerApp(ctk.CTk):
    _POLY_SIZES  = [50, 100, 200, 400, 800, 1200, 1600, 2000]
    _EXP_SIZES   = [5, 7, 9, 11, 13, 15, 17, 19, 20]
    _PROBE_SIZES = [5, 10, 15, 20]
    _EXP_RATIO   = 100

    # ------------------------------------------------------------------
    # Animated background
    # ------------------------------------------------------------------
    def _build_animated_bg(self, parent, flag):
        canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
        canvas.place(relwidth=1, relheight=1)
        setattr(self, flag, True)

        W = self.winfo_screenwidth()
        H = self.winfo_screenheight()

        # Particles
        PCOLS = ["#9b59b6", "#7f8ff4", "#38bdf8", "#e879f9",
                 "#c0c0c0", "#a78bfa", "#818cf8"]
        parts = []
        for _ in range(55):
            x = random.randint(0, W)
            y = random.randint(0, H)
            r = random.uniform(1.0, 2.8)
            oid = canvas.create_oval(x-r, y-r, x+r, y+r,
                                     fill=random.choice(PCOLS), outline="")
            parts.append({"id": oid, "x": x, "y": y, "r": r,
                          "speed": random.uniform(0.25, 0.9),
                          "drift": random.uniform(-0.3, 0.3)})

        def animate():
            if not getattr(self, flag):
                return
            for p in parts:
                p["y"] -= p["speed"]
                p["x"] += p["drift"]
                if p["y"] < -10:
                    p["y"] = H + 10
                    p["x"] = random.randint(0, W)
                x, y, r = p["x"], p["y"], p["r"]
                canvas.coords(p["id"], x-r, y-r, x+r, y+r)
            canvas.after(22, animate)

        animate()

        # Orbs
        orbs = []
        for ox, oy, orad, ocol in [
            (W * 0.72, H * 0.28, 160, "#3b0764"),
            (W * 0.28, H * 0.65, 130, "#1e1b4b"),
            (W * 0.55, H * 0.55, 100, "#4a044e"),
        ]:
            for i in range(5, 0, -1):
                r2 = orad * (i / 5)
                oid = canvas.create_oval(ox-r2, oy-r2, ox+r2, oy+r2,
                                         fill=ocol, outline="")
                orbs.append([oid, ox, oy, orad * (i / 5)])

        tick = [0]
        def pulse():
            if not getattr(self, flag):
                return
            tick[0] += 1
            sc = 1.0 + 0.06 * math.sin(tick[0] * 0.04)
            for o in orbs:
                oid, cx, cy, br = o
                r2 = br * sc
                canvas.coords(oid, cx-r2, cy-r2, cx+r2, cy+r2)
            canvas.after(30, pulse)

        pulse()

        return canvas, W, H

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _open_main_gui(self):
        self._particle_running = False
        self.start_page.destroy()
        self._build_ui()

    def _go_back(self):
        self._main_particle_running = False
        for w in self.winfo_children():
            w.destroy()
        self._default_cleared = False
        self._last_fig = self._last_res = self._last_sz = self._last_tm = None
        self._build_start_page()

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    def __init__(self):
        super().__init__()
        self.title("Algorithm Performance Evaluator")
        self.after(100, lambda: self.state("zoomed"))
        self.minsize(1200, 700)

        self.executor  = SafeExecutor()
        self.analyzer  = ComplexityAnalyzer()
        self._last_fig = self._last_res = self._last_sz = self._last_tm = None
        self._default_cleared       = False
        self._particle_running      = False
        self._main_particle_running = False

        self._build_start_page()

    # ------------------------------------------------------------------
    # Start Page
    # ------------------------------------------------------------------
    def _build_start_page(self):
        self.start_page = tk.Frame(self, bg=BG)
        self.start_page.place(relwidth=1, relheight=1)

        canvas, W, H = self._build_animated_bg(self.start_page, "_particle_running")
        self.bg_canvas = canvas

        # Grid — defined here so it's in scope for the Configure handler
        grid_lines = []

        def draw_grid(cw, ch):
            for lid in grid_lines:
                try:
                    canvas.delete(lid)
                except Exception:
                    pass
            grid_lines.clear()
            for gx in range(0, cw, 80):
                grid_lines.append(canvas.create_line(gx, 0, gx, ch, fill="#141428", width=1))
            for gy in range(0, ch, 80):
                grid_lines.append(canvas.create_line(0, gy, cw, gy, fill="#141428", width=1))

        draw_grid(W, H)

        # ── Center content ───────────────────────────────────────────────
        center = tk.Frame(canvas, bg=BG)

        # Place center window — stays centered and grid fills full canvas on resize
        center_win = canvas.create_window(0, 0, window=center, anchor="center")

        def on_canvas_resize(event):
            cw, ch = event.width, event.height
            canvas.coords(center_win, cw // 2, ch // 2)
            draw_grid(cw, ch)

        canvas.bind("<Configure>", on_canvas_resize)

        # Title card
        title_bg = tk.Frame(center, bg=PANEL,
                            highlightbackground=BORDER, highlightthickness=1,
                            padx=40, pady=28)
        title_bg.pack(pady=(20, 10))

        self._title_label = tk.Label(title_bg, text="",
                                     font=("Courier", 26, "bold"),
                                     fg=TEXT, bg=PANEL)
        self._title_label.pack()

        self._sub_label = tk.Label(title_bg, text="",
                                   font=("Courier", 12),
                                   fg=ACCENT, bg=PANEL)
        self._sub_label.pack(pady=(6, 0))

        # Typewriter
        full_title = "Algorithm Performance Evaluator"
        full_sub   = "▸ Visualize Time Complexity Like a Pro"
        self._tw_index = 0

        def type_title():
            if not self._particle_running:
                return
            if self._tw_index <= len(full_title):
                self._title_label.configure(
                    text=full_title[:self._tw_index] +
                         ("█" if self._tw_index < len(full_title) else ""))
                self._tw_index += 1
                canvas.after(48, type_title)
            else:
                self._tw_sub = 0
                def type_sub():
                    if not self._particle_running:
                        return
                    if self._tw_sub <= len(full_sub):
                        self._sub_label.configure(text=full_sub[:self._tw_sub])
                        self._tw_sub += 1
                        canvas.after(32, type_sub)
                    else:
                        canvas.after(200, show_cards)
                type_sub()

        # Feature cards
        cards_frame = tk.Frame(center, bg=BG)
        for i, (icon, label, accent) in enumerate([
            ("⚡", "Execution Engine",    ACCENT),
            ("📊", "Complexity Analyzer", "#0e7490"),
            ("📈", "Performance Graphs",  "#065f46"),
        ]):
            cf = tk.Frame(cards_frame, bg=PANEL,
                          highlightbackground=accent, highlightthickness=1,
                          padx=22, pady=14)
            cf.grid(row=0, column=i, padx=12)
            tk.Label(cf, text=icon,  font=("Arial", 20),        bg=PANEL).pack()
            tk.Label(cf, text=label, font=("Arial", 10, "bold"),
                     fg=TEXT, bg=PANEL).pack(pady=(4, 0))

        # Launch button
        btn_frame = tk.Frame(center, bg=BG)
        self._start_btn = tk.Button(
            btn_frame, text="  ▶  LAUNCH  ",
            bg=ACCENT, fg="white",
            font=("Courier", 13, "bold"),
            relief="flat", cursor="hand2",
            activebackground=ACCENT2, activeforeground="white",
            command=self._open_main_gui, padx=20, pady=10)
        self._start_btn.pack()

        self._btn_pulse = 0
        def pulse_btn():
            if not self._particle_running:
                return
            self._btn_pulse += 1
            cols = [ACCENT, "#a855f7", "#c084fc", "#a855f7", ACCENT]
            self._start_btn.configure(bg=cols[self._btn_pulse % len(cols)])
            btn_frame.after(300, pulse_btn)

        def show_cards():
            cards_frame.pack(pady=20)
            btn_frame.pack(pady=10)
            pulse_btn()

        canvas.after(300, type_title)

    # ------------------------------------------------------------------
    # Main UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        main_bg = tk.Frame(self, bg=BG)
        main_bg.place(relwidth=1, relheight=1)
        self._build_animated_bg(main_bg, "_main_particle_running")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left panel
        left_frame = ctk.CTkFrame(self, width=550, corner_radius=15,
                                   fg_color=PANEL,
                                   border_color=BORDER, border_width=1)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_frame.grid_propagate(False)

        header = ctk.CTkFrame(left_frame, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkButton(header, text="← Back", width=80, height=28,
                      fg_color=ACCENT, hover_color=ACCENT2,
                      text_color="white", font=ctk.CTkFont(size=12),
                      command=self._go_back).pack(side="left")

        ctk.CTkLabel(header, text="Algorithm Code",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=TEXT).pack(side="left", padx=15)

        self.code_editor = LineNumberedText(left_frame, height=25)
        self.code_editor.pack(fill="both", expand=True, padx=15, pady=10)
        self.code_editor.set_code(
            "# Write your function here\ndef my_function(arr):\n"
            "    return sorted(arr)\n")
        self.code_editor.text.bind("<FocusIn>", self._clear_default_code)
        self.code_editor.text.bind("<Key>",     self._clear_default_code)

        # Right panel
        right_frame = ctk.CTkFrame(self, corner_radius=15,
                                    fg_color=PANEL,
                                    border_color=BORDER, border_width=1)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)

        self.tabview = ctk.CTkTabview(
            right_frame, corner_radius=10,
            fg_color=PANEL,
            segmented_button_fg_color=BG,
            segmented_button_selected_color=ACCENT,
            segmented_button_selected_hover_color=ACCENT2,
            segmented_button_unselected_color=PANEL,
            segmented_button_unselected_hover_color=MUTED,
            text_color=TEXT)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.auto_tab   = self.tabview.add("🚀 Auto Mode")
        self.manual_tab = self.tabview.add("🎛️ Manual Mode")

        self._build_auto_tab()
        self._build_manual_tab()

    def _clear_default_code(self, event=None):
        if not self._default_cleared:
            self.code_editor.text.delete("1.0", "end")
            self._default_cleared = True

    # ------------------------------------------------------------------
    # Auto Tab
    # ------------------------------------------------------------------
    def _build_auto_tab(self):
        ctrl = ctk.CTkFrame(self.auto_tab, fg_color="transparent")
        ctrl.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(ctrl, text="Test case:", text_color=TEXT).pack(side="left", padx=(0, 10))
        self.case_var = ctk.StringVar(value="average")
        for val, col in [("best", "#22c55e"), ("average", "#3b82f6"), ("worst", "#ef4444")]:
            ctk.CTkRadioButton(ctrl, text=val.capitalize(),
                               variable=self.case_var, value=val,
                               fg_color=col, hover_color=col,
                               text_color=TEXT).pack(side="left", padx=5)

        self.auto_run_btn = ctk.CTkButton(
            ctrl, text="▶ Run Auto Analysis", command=self._run_auto,
            fg_color=ACCENT, hover_color=ACCENT2,
            text_color="white", font=ctk.CTkFont(size=13, weight="bold"))
        self.auto_run_btn.pack(side="right", padx=10)

        self.auto_status = ctk.CTkLabel(self.auto_tab, text="Ready",
                                         text_color=ACCENT3, anchor="w")
        self.auto_status.pack(fill="x", padx=15, pady=5)

        self.auto_graph_frame = ctk.CTkFrame(self.auto_tab, fg_color=BG,
                                              border_color=BORDER, border_width=1,
                                              corner_radius=10)
        self.auto_graph_frame.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkLabel(self.auto_graph_frame, text="Graph will appear here",
                     text_color=ACCENT).pack(expand=True)

        exp = ctk.CTkFrame(self.auto_tab, fg_color="transparent")
        exp.pack(fill="x", padx=15, pady=10)
        ctk.CTkButton(exp, text="💾 Export CSV", command=self._export_csv,
                      fg_color=MUTED, hover_color=BORDER,
                      text_color=TEXT, width=120).pack(side="left", padx=5)
        ctk.CTkButton(exp, text="🖼 Save Graph", command=self._export_graph,
                      fg_color=MUTED, hover_color=BORDER,
                      text_color=TEXT, width=120).pack(side="left", padx=5)

    # ------------------------------------------------------------------
    # Manual Tab
    # ------------------------------------------------------------------
    def _build_manual_tab(self):
        fixed = ctk.CTkFrame(self.manual_tab, corner_radius=10,
                              fg_color=PANEL, border_color=BORDER, border_width=1)
        fixed.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(fixed, text="Fixed Array (single run)",
                     font=ctk.CTkFont(weight="bold"), text_color=TEXT).pack(anchor="w", padx=10, pady=(10, 0))
        ctk.CTkLabel(fixed, text="Comma-separated integers:",
                     text_color=ACCENT3).pack(anchor="w", padx=10)
        self.manual_array_entry = ctk.CTkEntry(fixed, placeholder_text="5,2,8,1,9",
                                                fg_color=BG, border_color=ACCENT, text_color=TEXT)
        self.manual_array_entry.pack(fill="x", padx=10, pady=5)
        self.manual_array_entry.insert(0, "5,2,8,1,9")
        self.manual_run_btn = ctk.CTkButton(fixed, text="Run on this array",
                                             command=self._run_manual_fixed,
                                             fg_color=ACCENT, hover_color=ACCENT2, text_color="white")
        self.manual_run_btn.pack(pady=10)

        sweep = ctk.CTkFrame(self.manual_tab, corner_radius=10,
                              fg_color=PANEL, border_color=BORDER, border_width=1)
        sweep.pack(fill="x", padx=15, pady=10)
        ctk.CTkLabel(sweep, text="Custom Sizes Sweep",
                     font=ctk.CTkFont(weight="bold"), text_color=TEXT).pack(anchor="w", padx=10, pady=(10, 0))
        ctk.CTkLabel(sweep, text="Sizes (comma-separated):",
                     text_color=ACCENT3).pack(anchor="w", padx=10)
        self.manual_sizes_entry = ctk.CTkEntry(sweep, placeholder_text="100,200,400,800,1600",
                                                fg_color=BG, border_color=ACCENT, text_color=TEXT)
        self.manual_sizes_entry.pack(fill="x", padx=10, pady=5)
        self.manual_sizes_entry.insert(0, "100,200,400,800,1600")
        ctk.CTkLabel(sweep, text="Runs per size (1-20):",
                     text_color=ACCENT3).pack(anchor="w", padx=10)
        self.manual_runs_scale = ctk.CTkSlider(sweep, from_=1, to=20, number_of_steps=19,
                                                button_color=ACCENT, button_hover_color=ACCENT2,
                                                progress_color=BORDER)
        self.manual_runs_scale.set(10)
        self.manual_runs_scale.pack(fill="x", padx=10, pady=5)
        self.manual_sweep_btn = ctk.CTkButton(sweep, text="Run size sweep",
                                               command=self._run_manual_sweep,
                                               fg_color=ACCENT, hover_color=ACCENT2, text_color="white")
        self.manual_sweep_btn.pack(pady=10)

        self.manual_status = ctk.CTkLabel(self.manual_tab, text="Ready", text_color=ACCENT3)
        self.manual_status.pack(fill="x", padx=15, pady=5)

        self.manual_graph_frame = ctk.CTkFrame(self.manual_tab, fg_color=BG,
                                                border_color=BORDER, border_width=1,
                                                corner_radius=10)
        self.manual_graph_frame.pack(fill="both", expand=True, padx=15, pady=10)
        ctk.CTkLabel(self.manual_graph_frame, text="Graph will appear here",
                     text_color=ACCENT).pack(expand=True)

    # ------------------------------------------------------------------
    # Auto Logic
    # ------------------------------------------------------------------
    def _run_auto(self):
        self.auto_run_btn.configure(state="disabled", text="⏳ Running...")
        self._update_auto("Initialising...")
        threading.Thread(target=self._auto_worker, daemon=True).start()

    def _auto_worker(self):
        try:
            code = self.code_editor.get_code()
            if not code:
                self._update_auto("Error: empty code"); return
            case = self.case_var.get()
            self._update_auto("Probing growth rate...")
            probe_times = self.executor.probe_growth(code, self._PROBE_SIZES, timeout_sec=30)
            valid_p = [t for t in probe_times if t is not None and t > 0]
            is_exp  = len(valid_p) >= 2 and valid_p[-1] / valid_p[0] > self._EXP_RATIO
            sizes   = self._EXP_SIZES if is_exp else self._POLY_SIZES
            if is_exp:
                self._update_auto("Exponential growth detected → small n range")
            measured = []
            for n in sizes:
                self._update_auto(f"Benchmarking n = {n}...")
                elapsed, _ = self.executor.run(code, self._make_data(n, case), timeout_sec=10)
                measured.append((n, elapsed))
            valid = [(s, t) for s, t in measured if t is not None]
            if len(valid) < 3:
                self._update_auto("Too few valid measurements (timeouts?)"); return
            sz, tm = zip(*valid)
            sz, tm = list(sz), list(tm)
            res = self.analyzer.estimate(sz, tm)
            self._last_res, self._last_sz, self._last_tm = res, sz, tm
            self._draw_graph(self.auto_graph_frame, sz, tm, res)
            self._update_auto(
                f"Complexity: {res['complexity']}  |  Confidence: {res['confidence']:.2f}"
                f"  |  Log-log slope: {res['log_slope']:.4f}  |  R²: {res['r_squared']:.4f}"
                f"\n{res['interpretation']}")
        except Exception as e:
            self._update_auto(f"Error: {e}")
        finally:
            self.after(0, lambda: self.auto_run_btn.configure(
                state="normal", text="▶ Run Auto Analysis"))

    def _update_auto(self, text):
        self.after(0, lambda: self.auto_status.configure(text=text))

    # ------------------------------------------------------------------
    # Manual Logic
    # ------------------------------------------------------------------
    def _run_manual_fixed(self):
        self.manual_run_btn.configure(state="disabled")
        threading.Thread(target=self._manual_fixed_worker, daemon=True).start()

    def _manual_fixed_worker(self):
        try:
            code = self.code_editor.get_code()
            data = [int(x.strip()) for x in
                    self.manual_array_entry.get().strip().split(",") if x.strip()]
            if not data:
                self._update_manual("Empty input"); return
            elapsed, ret = self.executor.run(code, data, timeout_sec=10)
            if elapsed is None:
                self._update_manual("Execution failed or timed out")
            else:
                self._update_manual(f"Size: {len(data)} | Time: {elapsed:.4f} ms | Return: {ret}")
        except Exception as e:
            self._update_manual(f"Error: {e}")
        finally:
            self.after(0, lambda: self.manual_run_btn.configure(state="normal"))

    def _run_manual_sweep(self):
        self.manual_sweep_btn.configure(state="disabled")
        threading.Thread(target=self._manual_sweep_worker, daemon=True).start()

    def _manual_sweep_worker(self):
        try:
            code  = self.code_editor.get_code()
            sizes = [int(x.strip()) for x in
                     self.manual_sizes_entry.get().strip().split(",") if x.strip()]
            runs  = int(self.manual_runs_scale.get())
            times = []
            for n in sizes:
                self._update_manual(f"Benchmarking n = {n}...")
                elapsed, _ = self.executor.run(code, self._make_data(n, "average"),
                                               timeout_sec=10, runs=runs)
                times.append(elapsed)
            res = self.analyzer.estimate(sizes, times)
            self._draw_graph(self.manual_graph_frame, sizes, times, res)
            self._update_manual(f"Complexity: {res['complexity']} (R²={res['r_squared']:.3f})")
        except Exception as e:
            self._update_manual(f"Error: {e}")
        finally:
            self.after(0, lambda: self.manual_sweep_btn.configure(state="normal"))

    def _update_manual(self, text):
        self.after(0, lambda: self.manual_status.configure(text=text))

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------
    def _draw_graph(self, parent, sizes, times, res):
        complexity = res["complexity"]

        def plot():
            for w in parent.winfo_children():
                w.destroy()
            fig, ax = plt.subplots(figsize=(6.8, 4.4), dpi=100)
            fig.patch.set_facecolor(BG)
            ax.set_facecolor(PANEL)
            ax.plot(sizes, times, "o-", color=ACCENT3, lw=2, ms=5, label="Measured", zorder=3)
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
                        ax.plot(sizes, fitted, "--", color=ACCENT4, lw=1.8,
                                label=f"{complexity} fit", zorder=2)
                except:
                    pass
            if complexity == "O(1)":
                ax.set_xscale("linear"); ax.set_yscale("linear")
            elif complexity == "O(2ⁿ)":
                ax.set_xscale("linear"); ax.set_yscale("log")
            else:
                ax.set_xscale("log"); ax.set_yscale("log")
            ax.set_title(f"Time Complexity: {complexity}", color=TEXT,
                         fontsize=13, fontweight="bold")
            ax.set_xlabel("Input size (n)", color=ACCENT3)
            ax.set_ylabel("Time (ms)",      color=ACCENT3)
            ax.tick_params(colors="#7f8ff4")
            for spine in ax.spines.values():
                spine.set_edgecolor(BORDER)
            ax.grid(True, alpha=0.25, linestyle="--", color=BORDER)
            ax.legend(facecolor=PANEL, labelcolor=TEXT, edgecolor=BORDER)
            fig.tight_layout()
            cv = FigureCanvasTkAgg(fig, master=parent)
            cv.draw()
            cv.get_tk_widget().pack(fill="both", expand=True)
            self._last_fig = fig

        self.after(0, plot)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    @staticmethod
    def _make_data(n, case):
        return make_data(n, case)

    def _export_csv(self):
        if self._last_sz is None:
            messagebox.showinfo("Export", "Run an Auto analysis first"); return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        res = self._last_res or {}
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["complexity", "confidence", "log_slope", "r_squared"])
            w.writerow([res.get("complexity",""), res.get("confidence",""),
                        res.get("log_slope",""),  res.get("r_squared","")])
            w.writerow([])
            w.writerow(["input_size", "time_ms"])
            for s, t in zip(self._last_sz, self._last_tm):
                w.writerow([s, t])
        messagebox.showinfo("Export", f"Saved to {path}")

    def _export_graph(self):
        if self._last_fig is None:
            messagebox.showinfo("Export", "Run an Auto analysis first"); return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")])
        if not path:
            return
        self._last_fig.savefig(path, dpi=150, bbox_inches="tight",
                               facecolor=self._last_fig.get_facecolor())
        messagebox.showinfo("Export", f"Saved to {path}")


# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app = AlgorithmProfilerApp()
    app.mainloop()