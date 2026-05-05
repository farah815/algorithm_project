"""
start_page.py
=============
Animated landing page with typewriter title and launch button.
All canvas cleanup is safe – no Tcl errors.
"""

import tkinter as tk
import math
import random

from constants import BG, PANEL, BORDER, ACCENT, ACCENT2, ACCENT3, TEXT


class StartPage(tk.Frame):
    """Animated splash screen."""

    def __init__(self, master, switch_to_main):
        super().__init__(master, bg=BG)
        self.master = master
        self.switch_to_main = switch_to_main
        self._after_ids = []
        self._running = True

        self._build()
        self._start_animations()

    def _build(self):
        # Background canvas
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        self.canvas.place(relwidth=1, relheight=1)

        W = self.master.winfo_screenwidth()
        H = self.master.winfo_screenheight()

        # Particles
        PCOLS = ["#9b59b6", "#7f8ff4", "#38bdf8", "#e879f9", "#a78bfa", "#818cf8"]
        self._parts = []
        for _ in range(55):
            x, y = random.randint(0, W), random.randint(0, H)
            r    = random.uniform(1.0, 2.8)
            oid  = self.canvas.create_oval(x-r, y-r, x+r, y+r,
                                            fill=random.choice(PCOLS), outline="")
            self._parts.append({"id": oid, "x": x, "y": y, "r": r,
                                "speed": random.uniform(0.25, 0.9),
                                "drift": random.uniform(-0.3, 0.3)})

        # Glowing orbs
        self._orbs = []
        for ox, oy, orad, col in [
            (W*.72, H*.28, 160, "#3b0764"),
            (W*.28, H*.65, 130, "#1e1b4b"),
            (W*.55, H*.55, 100, "#4a044e"),
        ]:
            for i in range(5, 0, -1):
                r2  = orad * (i / 5)
                oid = self.canvas.create_oval(ox-r2, oy-r2, ox+r2, oy+r2,
                                             fill=col, outline="")
                self._orbs.append((oid, ox, oy, r2))
        self._tick = 0

        # Grid lines
        self._grid_ids = []
        self._draw_grid(W, H)
        self.canvas.bind("<Configure>", self._on_resize)

        # Centered content
        center = tk.Frame(self, bg=BG)
        center.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(center, bg=PANEL,
                        highlightbackground=BORDER, highlightthickness=1,
                        padx=40, pady=28)
        card.pack(pady=(20, 10))

        self._title_lbl = tk.Label(card, text="", font=("Courier", 26, "bold"),
                                   fg=TEXT, bg=PANEL)
        self._title_lbl.pack()
        self._sub_lbl = tk.Label(card, text="", font=("Courier", 12),
                                 fg=ACCENT3, bg=PANEL)
        self._sub_lbl.pack(pady=(6, 0))

        # Feature cards
        cards_frame = tk.Frame(center, bg=BG)
        for col, (icon, label, accent) in enumerate([
            ("⚡", "Execution Engine",    ACCENT),
            ("📊", "Complexity Analyzer", "#0e7490"),
            ("📈", "Performance Graphs",  "#065f46"),
        ]):
            cf = tk.Frame(cards_frame, bg=PANEL,
                          highlightbackground=accent, highlightthickness=1,
                          padx=22, pady=14)
            cf.grid(row=0, column=col, padx=12)
            tk.Label(cf, text=icon,  font=("Arial", 20),        bg=PANEL).pack()
            tk.Label(cf, text=label, font=("Arial", 10, "bold"),
                     fg=TEXT, bg=PANEL).pack(pady=(4, 0))
        cards_frame.pack(pady=20)

        # Launch button
        btn_frame = tk.Frame(center, bg=BG)
        self._start_btn = tk.Button(
            btn_frame, text="  ▶  LAUNCH  ",
            bg=ACCENT, fg="white",
            font=("Courier", 13, "bold"),
            relief="flat", cursor="hand2",
            activebackground=ACCENT2, activeforeground="white",
            command=self.switch_to_main,
            padx=20, pady=10,
        )
        self._start_btn.pack()
        btn_frame.pack(pady=10)

        self._typewriter_schedule()
        self._pulse_schedule()

    def _start_animations(self):
        self._anim_loop()

    def _anim_loop(self):
        if not self._running:
            return
        for p in self._parts:
            p["y"] -= p["speed"]
            p["x"] += p["drift"]
            if p["y"] < -10:
                p["y"] = self.winfo_height() + 10
                p["x"] = random.randint(0, self.winfo_width())
            x, y, r = p["x"], p["y"], p["r"]
            try:
                self.canvas.coords(p["id"], x-r, y-r, x+r, y+r)
            except Exception:
                return
        self._tick += 1
        sc = 1.0 + 0.06 * math.sin(self._tick * 0.04)
        for oid, cx, cy, br in self._orbs:
            r2 = br * sc
            try:
                self.canvas.coords(oid, cx-r2, cy-r2, cx+r2, cy+r2)
            except Exception:
                return
        self._after_ids.append(self.canvas.after(22, self._anim_loop))

    def _typewriter_schedule(self):
        self._type_index = 0
        self._type_sub_index = 0
        FULL_TITLE = "Algorithm Performance Evaluator"
        FULL_SUB   = "▸ Visualize Time Complexity Like a Pro"

        def type_title():
            if not self._running:
                return
            self._title_lbl.config(text=FULL_TITLE[:self._type_index] +
                                   ("█" if self._type_index < len(FULL_TITLE) else ""))
            self._type_index += 1
            if self._type_index <= len(FULL_TITLE):
                self._after_ids.append(self.canvas.after(48, type_title))
            else:
                self.canvas.after(150, type_sub)

        def type_sub():
            if not self._running:
                return
            self._sub_lbl.config(text=FULL_SUB[:self._type_sub_index])
            self._type_sub_index += 1
            if self._type_sub_index <= len(FULL_SUB):
                self._after_ids.append(self.canvas.after(32, type_sub))

        self._after_ids.append(self.canvas.after(300, type_title))

    def _pulse_schedule(self):
        pulse_colors = [ACCENT, "#a855f7", "#c084fc", "#a855f7"]
        pc = [0]
        def pulse_btn():
            if not self._running:
                return
            self._start_btn.configure(bg=pulse_colors[pc[0] % len(pulse_colors)])
            pc[0] += 1
            self._after_ids.append(self.canvas.after(300, pulse_btn))
        self._after_ids.append(self.canvas.after(300, pulse_btn))

    def _on_resize(self, event):
        self._draw_grid(event.width, event.height)

    def _draw_grid(self, w, h):
        for gid in self._grid_ids:
            try:
                self.canvas.delete(gid)
            except Exception:
                pass
        self._grid_ids.clear()
        for gx in range(0, w, 80):
            self._grid_ids.append(self.canvas.create_line(gx, 0, gx, h, fill="#141428"))
        for gy in range(0, h, 80):
            self._grid_ids.append(self.canvas.create_line(0, gy, w, gy, fill="#141428"))

    def destroy(self):
        self._running = False
        for aid in self._after_ids:
            try:
                self.master.after_cancel(aid)
            except Exception:
                pass
        self._after_ids.clear()
        try:
            super().destroy()
        except tk.TclError:
            pass