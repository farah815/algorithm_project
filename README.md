# Algorithm Performance Evaluator

## 📌 Project Title
Algorithm Performance Evaluator

## 📖 Overview
A Python desktop application designed to measure and estimate the Big-O time complexity of user-provided Python functions. The tool executes code in a safe subprocess, collects timing data across varying input sizes, and applies log-log slope regression to determine complexity classes. Targeted at students, educators, and anyone learning algorithms, it provides visual feedback through graphical output comparing measured performance against theoretical curves.

## ✨ Features
- Code editor with syntax highlighting and line numbers.
- Dropdown menu of ready-to-test algorithm examples (Bubble Sort, QuickSort, Merge Sort, etc.).
- Auto Analysis mode – automatic sweep of input sizes with real-time progress.
- Manual Benchmarks – run a single array or a custom size sweep.
- Animated start page with typewriter effect.
- Graphical output with measured data and fitted theoretical curve.
- Export results to CSV and graphs to PNG/PDF.
- Keyboard shortcuts (Enter to run, Ctrl+Enter for Auto Analysis).
- Safe subprocess execution – user code cannot crash the GUI.

## 🖥️ Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/algorithm-performance-evaluator.git
   cd algorithm-performance-evaluator
   ```
(Optional) Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```
Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 Usage
Run the application:
   ```bash
   python app.py
   ```
On the start page, click LAUNCH.

In the main window:
- Write your own function in the code editor, or select an example from the dropdown.
- Choose a test case (Best / Average / Worst).
- Press Ctrl+Enter or click ▶ Run Auto to perform a full complexity analysis.
- Switch to the Manual Benchmarks tab for single runs or custom sweeps.
- View the graph, detected complexity, and confidence score.
- Export the data or graph using the buttons below the graph.

## 🧩 Project Structure
```
.
├── app.py                # Main application entry point (orchestrator)
├── start_page.py         # Animated landing page
├── main_page.py          # Main tool UI (code editor, tabs, graph, workers)
├── constants.py          # Theme colours, default code, algorithm examples
├── gui_components.py     # Line-numbered code editor with syntax highlighting
├── executor.py           # Safe subprocess execution & timing
├── analyzer.py           # Big‑O detection (log‑log slope, polynomial fit, etc.)
├── models.py             # Complexity class definitions (O(1), O(n), …)
├── data_generator.py     # Test array generation (best/average/worst)
├── screenshots/          # UI screenshots (used in documentation)
├── requirements.txt      # Python dependencies
└── README.md
```

## 🧠 Architecture
Brief description of the four core modules:

**GUI Layer** – CustomTkinter interface, handles user input and displays results.

**Execution Engine** – runs user code in a subprocess, measures timing.

**Data Generator** – provides test arrays for the selected case.

**Performance Analyzer** – applies regression and rule‑based logic to estimate complexity.

Include the ASCII architecture diagram:
```
               User Input (code, test case)
                             |
                             v
                  +-------------------+
                  |    GUI Layer      |
                  +-------------------+
                              |
                  code, configuration
                              |
                              v
                  +-------------------+      +----------------+
                  | Execution Engine  | <--- | Data Generator |
                  +-------------------+      +----------------+
                          |                         |
               (input sizes, times)        provides test arrays
                          |
                          v
                +---------------------+
                | Performance Analyzer|
                +---------------------+
                          |
        complexity class, confidence, graph
                          |
                          v
                +-------------------+
                |    GUI Layer      |
                +-------------------+
                          |
                     user display
```

## 📊 Test Results
A table showing expected vs detected complexity for the pre‑loaded examples:

| Algorithm              | Expected Complexity | Detected Complexity | Confidence |
|------------------------|---------------------|---------------------|------------|
| Bubble Sort            | O(n²)               | O(n²)               | 0.99       |
| Selection Sort         | O(n²)               | O(n²)               | 0.99       |
| Insertion Sort         | O(n²)               | O(n²)               | 0.98       |
| Shell Sort             | O(n log n)          | O(n log n)          | 0.97       |
| Quick Sort (iter.)     | O(n log n)          | O(n log n)          | 0.97       |
| Merge Sort (iter.)     | O(n log n)          | O(n log n)          | 0.98       |
| Linear Scan (max)      | O(n)                | O(n)                | 0.96       |
| Binary Search          | O(log n)            | O(log n)            | 0.95       |

*Note: Detection accuracy is consistently high (>95%) for standard implementations due to robust log-log regression and outlier filtering.*

## 🧑‍🤝‍🧑 Team
- **Raghda Gad** – Backend Development
- **Farah Fayez** – GUI & Integration
- **Noran Salm** – Optimisation & Documentation

## 📜 License
This project is licensed under the MIT License – see the LICENSE file for details.
