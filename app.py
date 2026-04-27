from main import Main
from engine import Engine 
from data_generator import DataGenerator
from analyzer import Analyzer
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

app = Main()

window = tk.Tk()
window.title("Algorithm Performance Evaluator")
window.state("zoomed")
window.configure(bg="#0b0c1a")

# =========================
# MODE STATE
# =========================
mode = {"type": None, "ready": False}
selected_case = {"type": None}

# =========================
# BACKGROUND CANVAS
# =========================
bg_canvas = tk.Canvas(window, bg="#0b0c1a", highlightthickness=0)
bg_canvas.pack(fill="both", expand=True)

bg_canvas.create_oval(750, 120, 1050, 420, fill="#1f6f3f", outline="")
bg_canvas.create_oval(450, 380, 750, 680, fill="#145a32", outline="")

# =========================
# START PAGE
# =========================
start_page = tk.Frame(window, bg="#0b0c1a")
start_page.place(relwidth=1, relheight=1)

bg_canvas.create_window(
    window.winfo_screenwidth() // 2,
    window.winfo_screenheight() // 2,
    window=start_page
)

title_card = tk.Frame(start_page, bg="#15162b", padx=30, pady=25)
title_card.pack(pady=70)

tk.Label(title_card,
         text="Algorithm Performance Evaluator",
         font=("Arial", 26, "bold"),
         fg="white", bg="#15162b").pack()

tk.Label(title_card,
         text="Visualize Time Complexity Like a Pro",
         font=("Arial", 12),
         fg="#aaaaaa", bg="#15162b").pack()

cards = tk.Frame(start_page, bg="#0b0c1a")
cards.pack(pady=25)

def card(text):
    return tk.Label(cards, text=text,
                    font=("Arial", 11),
                    fg="white", bg="#1e213a",
                    padx=18, pady=12)

card("⚡ Execution Engine").grid(row=0, column=0, padx=10)
card("📊 Complexity Analyzer").grid(row=0, column=1, padx=10)
card("📈 Performance Graphs").grid(row=0, column=2, padx=10)

# =========================
# GRAPH FUNCTION
# =========================
def show_single_graph(sizes, values, label, color):
    plt.close("all")
    for widget in graph_box.winfo_children():
        widget.destroy()

    fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
    ax.plot(sizes, values, marker="o", label=label, color=color)
    ax.set_title(f"{label} Complexity Graph")
    ax.set_xlabel("Input Size")
    ax.set_ylabel("Execution Time (ms)")
    ax.legend()

    canvas = FigureCanvasTkAgg(fig, master=graph_box)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)

# =========================
# CASE SELECTION
# =========================
def run_case(case_type):
    selected_case["type"] = case_type
    result_label.config(text=f"Selected Case: {case_type}")

def clear_graph():
    for widget in graph_box.winfo_children():
        widget.destroy()

# =========================
# MAIN PAGE
# =========================
main_page = tk.Frame(window, bg="#0b0c1a")

left = tk.Frame(main_page, bg="#11132a", width=520, height=600)
left.pack(side="left", fill="both", expand=True)
left.pack_propagate(False)

tk.Label(left, text="Input & Controls",
         font=("Arial", 16, "bold"),
         fg="white", bg="#11132a").pack(pady=10)

code_box = tk.Text(left, bg="#0b0c1a", fg="white",
                   insertbackground="white",
                   font=("Consolas", 12),
                   height=22, width=60)
code_box.pack(fill="x", padx=15, pady=10)
code_box.insert("1.0", "write your code here...")

input_label = tk.Label(left, text="Input Array", fg="white", bg="#11132a")
input_box = tk.Entry(left, font=("Arial", 12), width=35)

case_frame = tk.Frame(left, bg="#11132a")
tk.Button(case_frame, text="Best Case",
          bg="#22c55e", fg="white",
          width=15,
          command=lambda: run_case("best")).grid(row=0, column=0, padx=10)
tk.Button(case_frame, text="Average Case",
          bg="#3b82f6", fg="white",
          width=15,
          command=lambda: run_case("average")).grid(row=0, column=1, padx=10)
tk.Button(case_frame, text="Worst Case",
          bg="#ef4444", fg="white",
          width=15,
          command=lambda: run_case("worst")).grid(row=0, column=2, padx=10)

# =========================
# RUN ANALYSIS (FIXED)
# =========================
def run_analysis():
    window.update_idletasks()
    user_code = code_box.get("1.0", "end").strip()
    user_input = input_box.get().strip()

    try:
        # ================= MANUAL =================
        if mode["type"] == "manual":

            clear_graph()

            tk.Label(
                graph_box,
                text="No graph in Manual Mode",
                fg="gray",
                bg="#0b0c1a"
            ).pack(expand=True)

            result = app.run_manual(user_code, user_input)

            result_label.config(
                text=(
                    f"Execution Time: {result['execution_time']} ms | "
                    f"Size: {result['input_size']} | "
                    f"Return: {result['return_value']}"
                )
            )

        # ================= AUTO =================
        else:
            case = selected_case["type"]

            if case is None:
                result_label.config(text="⚠ Please select Best / Average / Worst case first")
                return

            sizes = [100, 500, 1000, 2000, 5000]
            result = app.run_auto(user_code, sizes=sizes)

            if case == "best":
                times = result["best_times"]
                color = "green"
                label = "Best Case"
            elif case == "average":
                times = result["avg_times"]
                color = "blue"
                label = "Average Case"
            else:
                times = result["worst_times"]
                color = "red"
                label = "Worst Case"

            show_single_graph(result["sizes"], times, label, color)

            result_label.config(
                text=f"Complexity: {result['complexity']} | Slope: {result['slope']}"
            )

    except Exception as e:
        result_label.config(text=f"Error: {e}")

# =========================
# BUTTON
# =========================
tk.Button(left, text="▶ Run Analysis",
          bg="#f59e0b", fg="black",
          font=("Arial", 12, "bold"),
          width=20,
          command=run_analysis).pack(pady=15)

# =========================
# RIGHT PANEL
# =========================
right = tk.Frame(main_page, bg="#0f1224")
right.pack(side="right", fill="both", expand=True)

tk.Label(right, text="Results Panel",
         font=("Arial", 16, "bold"),
         fg="white", bg="#0f1224").pack(pady=10)

graph_box = tk.Frame(right, bg="#0b0c1a", height=420)
graph_box.pack(fill="x", padx=20, pady=20)
graph_box.pack_propagate(False)

tk.Label(graph_box, text="Graph will appear here",
         fg="gray", bg="#0b0c1a").pack(expand=True)

result_label = tk.Label(right,
                        text="Complexity: (not analyzed yet)",
                        fg="#22c55e",
                        bg="#0f1224",
                        font=("Arial", 13, "bold"))
result_label.pack(pady=10)

# =========================
# NAVIGATION
# =========================
def go_back():
    main_page.place_forget()
    bg_canvas.pack(fill="both", expand=True)
    start_page.place(relwidth=1, relheight=1)

tk.Button(right, text="⬅ Back", command=go_back).pack(pady=20)

def set_manual():
    input_label.pack(pady=(10, 5))
    input_box.pack(pady=(0, 15))
    case_frame.pack_forget()

def set_auto():
    input_label.pack_forget()
    input_box.pack_forget()
    case_frame.pack(pady=10)

def go_to_main(selected_mode):
    mode["type"] = selected_mode
    start_page.place_forget()
    bg_canvas.pack_forget()
    main_page.place(relwidth=1, relheight=1)

    if selected_mode == "manual":
        set_manual()
    else:
        set_auto()

    result_label.config(text="Complexity: (not analyzed yet)")

btn_frame = tk.Frame(start_page, bg="#0b0c1a")
btn_frame.pack(pady=35)

tk.Button(btn_frame, text="START WITH MANUAL",
          command=lambda: go_to_main("manual")).grid(row=0, column=0, padx=10)
tk.Button(btn_frame, text="START WITH AUTO",
          command=lambda: go_to_main("auto")).grid(row=0, column=1, padx=10)

main_page.lower()
window.mainloop()