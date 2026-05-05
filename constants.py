"""
constants.py
============
Shared colours, default code, algorithm examples.
"""

BG      = "#07080f"
PANEL   = "#0d0e1f"
BORDER  = "#3730a3"
ACCENT  = "#7c3aed"
ACCENT2 = "#6d28d9"
ACCENT3 = "#a78bfa"
ACCENT4 = "#f472b6"
TEXT    = "#e2e8f0"
MUTED   = "#1e1b4b"
GREEN   = "#22c55e"
RED     = "#ef4444"

_DEFAULT_CODE = (
    "# Write your function here\n"
    "def my_function(arr):\n"
    "    return sorted(arr)\n"
)

ALGORITHM_EXAMPLES = {
    "Select an example...": _DEFAULT_CODE,
    "Quicksort (recursive)": (
        "def quick_sort(arr):\n"
        "    if len(arr) <= 1:\n"
        "        return arr\n"
        "    pivot = arr[len(arr) // 2]\n"
        "    left = [x for x in arr if x < pivot]\n"
        "    mid  = [x for x in arr if x == pivot]\n"
        "    right = [x for x in arr if x > pivot]\n"
        "    return quick_sort(left) + mid + quick_sort(right)\n"
    ),
    "Quicksort (iterative)": (
        "def quick_sort_iter(arr):\n"
        "    if len(arr) <= 1:\n"
        "        return arr\n"
        "    stack = [(0, len(arr) - 1)]\n"
        "    arr = list(arr)\n"
        "    while stack:\n"
        "        low, high = stack.pop()\n"
        "        if low < high:\n"
        "            pivot = arr[(low + high) // 2]\n"
        "            i, j = low, high\n"
        "            while i <= j:\n"
        "                while arr[i] < pivot: i += 1\n"
        "                while arr[j] > pivot: j -= 1\n"
        "                if i <= j:\n"
        "                    arr[i], arr[j] = arr[j], arr[i]\n"
        "                    i += 1; j -= 1\n"
        "            if low < j: stack.append((low, j))\n"
        "            if i < high: stack.append((i, high))\n"
        "    return arr\n"
    ),
    "Merge Sort": (
        "def merge_sort(arr):\n"
        "    if len(arr) <= 1:\n"
        "        return arr\n"
        "    mid = len(arr) // 2\n"
        "    left = merge_sort(arr[:mid])\n"
        "    right = merge_sort(arr[mid:])\n"
        "    return merge(left, right)\n\n"
        "def merge(left, right):\n"
        "    result = []\n"
        "    i = j = 0\n"
        "    while i < len(left) and j < len(right):\n"
        "        if left[i] <= right[j]:\n"
        "            result.append(left[i]); i += 1\n"
        "        else:\n"
        "            result.append(right[j]); j += 1\n"
        "    result.extend(left[i:])\n"
        "    result.extend(right[j:])\n"
        "    return result\n"
    ),
    "Bubble Sort": (
        "def bubble_sort(arr):\n"
        "    n = len(arr)\n"
        "    for i in range(n):\n"
        "        swapped = False\n"
        "        for j in range(0, n-i-1):\n"
        "            if arr[j] > arr[j+1]:\n"
        "                arr[j], arr[j+1] = arr[j+1], arr[j]\n"
        "                swapped = True\n"
        "        if not swapped:\n"
        "            break\n"
        "    return arr\n"
    ),
    "Insertion Sort": (
        "def insertion_sort(arr):\n"
        "    for i in range(1, len(arr)):\n"
        "        key = arr[i]\n"
        "        j = i - 1\n"
        "        while j >= 0 and arr[j] > key:\n"
        "            arr[j + 1] = arr[j]\n"
        "            j -= 1\n"
        "        arr[j + 1] = key\n"
        "    return arr\n"
    ),
    "Binary Search (sorted input)": (
        "def binary_search(arr):\n"
        "    target = arr[len(arr)//3]\n"
        "    lo, hi = 0, len(arr)-1\n"
        "    while lo <= hi:\n"
        "        mid = (lo + hi) // 2\n"
        "        if arr[mid] == target:\n"
        "            return mid\n"
        "        elif arr[mid] < target:\n"
        "            lo = mid + 1\n"
        "        else:\n"
        "            hi = mid - 1\n"
        "    return -1\n"
    ),
    "Linear Search (max element)": (
        "def linear_search(arr):\n"
        "    max_val = arr[0]\n"
        "    for x in arr:\n"
        "        if x > max_val:\n"
        "            max_val = x\n"
        "    return max_val\n"
    ),
}