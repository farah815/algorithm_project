"""
app.py – Algorithm Performance Evaluator

Orchestrator: switches between StartPage and MainPage.
No more overlapping pages – old page is fully removed first.
"""

import tkinter as tk
import customtkinter as ctk

from constants import BG
from start_page import StartPage
from main_page import MainPage

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class AlgorithmProfilerApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("Algorithm Performance Evaluator")
        self.after(100, lambda: self.state("zoomed"))
        self.minsize(1200, 700)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._setup_tk_error_handler()

        self._current_page = None
        self._build_start_page()

    def _setup_tk_error_handler(self):
        """Suppress harmless Tcl teardown errors."""
        original = self.report_callback_exception

        def handler(exc_type, exc_value, exc_tb):
            err = str(exc_value)
            if "invalid command name" in err or "can't invoke \"tk\" command" in err:
                return
            original(exc_type, exc_value, exc_tb)

        self.report_callback_exception = handler

    # ── Safe page destruction ─────────────────────────────────────────

    def _safe_destroy_current_page(self):
        if self._current_page:
            try:
                self._current_page.pack_forget()   # remove from layout
                self._current_page.destroy()
            except tk.TclError:
                pass
            self._current_page = None

    # ── Page navigation ───────────────────────────────────────────────

    def _build_start_page(self):
        self._safe_destroy_current_page()
        self._current_page = StartPage(self, switch_to_main=self._build_main_page)
        self._current_page.pack(fill="both", expand=True)

    def _build_main_page(self):
        self._safe_destroy_current_page()
        self._current_page = MainPage(self, switch_to_start=self._build_start_page)
        self._current_page.pack(fill="both", expand=True)

    def _on_close(self):
        self._safe_destroy_current_page()
        try:
            self.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    app = AlgorithmProfilerApp()
    app.mainloop()