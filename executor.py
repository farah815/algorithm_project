"""
executor.py
===========
Isolated, noise-resistant function timer.

Why a subprocess?
-----------------
Running user code in a child process prevents:
  - Infinite loops from freezing the GUI
  - Syntax errors / exceptions from crashing the app
  - Global state contamination between runs

Why pre-created copies?
-----------------------
Previous versions allocated `list(data)` just before `start = perf_counter()`.
That allocation flushes the CPU cache, adding O(n) overhead to every run.
For an O(1) function at n=2000 this overhead is ~6 µs and grows with n,
producing a false upward trend.  Fix: create all `runs+1` copies once,
before any timing starts.

Why median of 7?
----------------
OS scheduling can inflate any single sample by 3-10×.  Median of 7 is
robust to up to 3 outliers.  One warmup run is discarded (cold-start,
import caching, branch predictor warm-up).
"""

import subprocess
import sys
import tempfile
import os
import json
import textwrap


class SafeExecutor:
    """Execute user-supplied Python code safely in a subprocess."""

    # ------------------------------------------------------------------ #
    # Public interface                                                      #
    # ------------------------------------------------------------------ #

    @staticmethod
    def run(
        user_code: str,
        data: list,
        timeout_sec: float = 10.0,
        runs: int = 7,
    ) -> tuple[float | None, object]:
        """
        Time `user_code(data)` and return (median_ms, return_value).

        Parameters
        ----------
        user_code   : Python source containing exactly one callable.
        data        : Input list for that callable.
        timeout_sec : Wall-clock deadline for the entire subprocess.
        runs        : Timed repetitions (median returned).

        Returns
        -------
        (median_time_ms, return_value)  or  (None, None) on any failure.
        """
        script = textwrap.dedent(f"""
            import sys, json, time, statistics

            user_code     = {json.dumps(user_code)}
            original_data = {json.dumps(data)}
            runs          = {runs}

            # ── Compile user code and locate the function ────────────
            env = {{}}
            exec(user_code, {{}}, env)
            func = next((v for v in env.values() if callable(v)), None)
            if func is None:
                print(json.dumps({{"error": "No callable function found"}}))
                sys.exit(1)

            # ── Pre-create ALL copies before any timing begins ────────
            # Allocating list(n) flushes the CPU cache. If the copy is
            # created inside the timing loop, even arr[0] appears slow
            # for large n, producing a false O(n) trend in O(1) code.
            # Creating copies here separates allocation from timing.
            copies = [list(original_data) for _ in range(runs + 1)]

            # ── Warmup: run once, discard ─────────────────────────────
            func(copies[0])

            # ── Timed runs ────────────────────────────────────────────
            samples, result = [], None
            for i in range(1, runs + 1):
                t0     = time.perf_counter()
                result = func(copies[i])
                samples.append((time.perf_counter() - t0) * 1_000.0)

            print(json.dumps({{"time_ms": statistics.median(samples),
                               "result":  str(result)}}))
        """)
        return SafeExecutor._run_script(script, timeout_sec)

    @staticmethod
    def probe_growth(
        user_code: str,
        probe_sizes: list[int],
        timeout_sec: float = 30.0,
    ) -> list[float | None]:
        """
        Measure execution time at several sizes inside ONE subprocess.

        Spawning a separate subprocess per size adds ~150 ms overhead
        per call.  For fib(5) ≈ 0.001 ms that overhead dominates, so
        ratio ≈ 1.0 and exponential growth goes undetected.  Running
        all probe sizes in a single subprocess eliminates that bias.

        Returns
        -------
        List of times (ms) in the same order as probe_sizes.
        None entries mark failed / timed-out sizes.
        """
        script = textwrap.dedent(f"""
            import sys, json, time

            user_code   = {json.dumps(user_code)}
            probe_sizes = {json.dumps(probe_sizes)}

            env = {{}}
            exec(user_code, {{}}, env)
            func = next((v for v in env.values() if callable(v)), None)
            if func is None:
                print(json.dumps({{"times": [None]*len(probe_sizes)}}))
                sys.exit(0)

            times = []
            for n in probe_sizes:
                try:
                    data = list(range(n))
                    func(list(data))               # warmup for this size
                    t0 = time.perf_counter()
                    func(list(data))
                    times.append((time.perf_counter() - t0) * 1_000.0)
                except Exception:
                    times.append(None)

            print(json.dumps({{"times": times}}))
        """)
        return SafeExecutor._probe_script(script, timeout_sec, len(probe_sizes))

    # ------------------------------------------------------------------ #
    # Private helpers                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _write_and_run(script: str, timeout_sec: float) -> subprocess.CompletedProcess | None:
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                tmp = f.name
                f.write(script)
            return subprocess.run(
                [sys.executable, tmp],
                capture_output=True, text=True, timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    @staticmethod
    def _run_script(script: str, timeout_sec: float) -> tuple[float | None, object]:
        proc = SafeExecutor._write_and_run(script, timeout_sec)
        if proc is None or proc.returncode != 0 or not proc.stdout.strip():
            return None, None
        try:
            out = json.loads(proc.stdout.strip())
            if "error" in out:
                return None, None
            return float(out["time_ms"]), out.get("result")
        except (json.JSONDecodeError, KeyError, TypeError):
            return None, None

    @staticmethod
    def _probe_script(script: str, timeout_sec: float, n: int) -> list[float | None]:
        proc = SafeExecutor._write_and_run(script, timeout_sec)
        if proc is None or proc.returncode != 0 or not proc.stdout.strip():
            return [None] * n
        try:
            return json.loads(proc.stdout.strip()).get("times", [None] * n)
        except (json.JSONDecodeError, KeyError):
            return [None] * n
