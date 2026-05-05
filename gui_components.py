"""
gui_components.py
=================
Reusable GUI widgets for the Algorithm Performance Evaluator.

- highlight_syntax    : syntax highlighting for a tkinter Text widget
- LineNumberedText    : code editor with line numbers (improved readability)
"""

import tkinter as tk
import customtkinter as ctk

# ── Color constants ──────────────────────────────────────────────────────────

COLORS = {
    "keyword": "#ff79c6",
    "string":  "#50fa7b",
    "comment": "#6272a4",
    "number":  "#bd93f9",
    "bg_code": "#0b0c1a",
    "fg_code": "#e2e8f0",
}

# ── Syntax highlighting ──────────────────────────────────────────────────────

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
        if "#" in line:
            idx = line.index("#")
            text_widget.tag_add("comment", f"{i}.{idx}", f"{i}.end")
            line = line[:idx]
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


# ── Code editor with line numbers ────────────────────────────────────────────

class LineNumberedText(ctk.CTkFrame):
    """Code editor with line numbers (wraps tkinter Text)."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent")

        # Sensible defaults (overridable by caller)
        kwargs.setdefault("font", ("Consolas", 12))
        kwargs.setdefault("spacing1", 2)
        kwargs.setdefault("bg", COLORS["bg_code"])
        kwargs.setdefault("fg", COLORS["fg_code"])
        kwargs.setdefault("insertbackground", COLORS["fg_code"])
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("padx", 8)
        kwargs.setdefault("pady", 6)

        self.text = tk.Text(self, wrap="none", undo=True, **kwargs)

        self.line_numbers = tk.Text(self, width=5, wrap="none", takefocus=0,
                                    bg="#1a1d35", fg="#94a3b8",
                                    font=kwargs["font"],
                                    relief="flat", padx=3, pady=6)
        self.line_numbers.pack(side="left", fill="y")
        self.text.pack(side="right", fill="both", expand=True)

        self.text.bind("<KeyRelease>",  self._on_change)
        self.text.bind("<MouseWheel>",  self._scroll)
        self.text.bind("<Button-4>",    self._scroll)
        self.text.bind("<Button-5>",    self._scroll)
        self.text.bind("<Configure>",   self._on_change)
        self.text.bind("<Tab>",         self._tab_press)
        self.text.bind("<Control-z>",   self._undo)
        self.text.bind("<Control-y>",   self._redo)

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