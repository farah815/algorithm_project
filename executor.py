"""
executor.py
===========
Isolated, noise-resistant function timer.

Now also returns stderr on failure so the GUI can display errors.
Recursion limit raised to 10 000 to allow recursive algorithms (like quick sort)
to process larger inputs without hitting RecursionError.
"""

import subprocess
import sys
import tempfile
import os
import json
import textwrap


class SafeExecutor:
    """Execute user-supplied Python code safely in a subprocess."""

    @staticmethod
    def run(
        user_code: str,
        data: list,
        timeout_sec: float = 10.0,
        runs: int = 7,
    ) -> tuple[float | None, object, str]:
        """
        Returns (median_ms, return_value, stderr).
        On success, stderr is empty.
        On failure, median_ms is None and stderr contains the error output.
        """
        script = textwrap.dedent(f"""
            import sys, json, time, statistics, traceback
            sys.setrecursionlimit(10000)

            user_code     = {json.dumps(user_code)}
            original_data = {json.dumps(data)}
            runs          = {runs}

            try:
                env = {{}}
                exec(user_code, {{}}, env)
                func = next((v for v in env.values() if callable(v)), None)
                if func is None:
                    print(json.dumps({{"error": "No callable function found"}}))
                    sys.exit(1)

                copies = [list(original_data) for _ in range(runs + 1)]
                func(copies[0])   # warmup

                samples, result = [], None
                for i in range(1, runs + 1):
                    t0     = time.perf_counter()
                    result = func(copies[i])
                    samples.append((time.perf_counter() - t0) * 1_000.0)

                print(json.dumps({{"time_ms": statistics.median(samples),
                                   "result":  str(result)}}))
            except Exception as e:
                print(json.dumps({{"error": traceback.format_exc()}}))
                sys.exit(1)
        """)
        return SafeExecutor._run_script(script, timeout_sec)

    @staticmethod
    def probe_growth(
        user_code: str,
        probe_sizes: list[int],
        timeout_sec: float = 30.0,
    ) -> tuple[list[float | None], str]:
        """
        Returns (times_list, stderr).
        """
        script = textwrap.dedent(f"""
            import sys, json, time, traceback
            sys.setrecursionlimit(10000)

            user_code   = {json.dumps(user_code)}
            probe_sizes = {json.dumps(probe_sizes)}

            try:
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
                        func(list(data))
                        t0 = time.perf_counter()
                        func(list(data))
                        times.append((time.perf_counter() - t0) * 1_000.0)
                    except Exception:
                        times.append(None)

                print(json.dumps({{"times": times}}))
            except Exception as e:
                print(json.dumps({{"error": traceback.format_exc()}}))
                sys.exit(1)
        """)
        return SafeExecutor._probe_script(script, timeout_sec, len(probe_sizes))

    @staticmethod
    def _write_and_run(script: str, timeout_sec: float):
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                tmp = f.name
                f.write(script)
            proc = subprocess.run(
                [sys.executable, tmp],
                capture_output=True, text=True, timeout=timeout_sec,
            )
            return proc
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
    def _run_script(script: str, timeout_sec: float) -> tuple[float | None, object, str]:
        proc = SafeExecutor._write_and_run(script, timeout_sec)
        if proc is None:
            return None, None, "Subprocess timed out or could not start."
        stderr = proc.stderr.strip()
        if proc.returncode != 0 or not proc.stdout.strip():
            return None, None, stderr if stderr else "Unknown error (return code {})".format(proc.returncode)
        try:
            out = json.loads(proc.stdout.strip())
            if "error" in out:
                return None, None, out["error"]
            return float(out["time_ms"]), out.get("result"), ""
        except (json.JSONDecodeError, KeyError, TypeError):
            return None, None, "Invalid JSON output from subprocess."

    @staticmethod
    def _probe_script(script: str, timeout_sec: float, n: int) -> tuple[list[float | None], str]:
        proc = SafeExecutor._write_and_run(script, timeout_sec)
        if proc is None:
            return [None] * n, "Subprocess timed out or could not start."
        stderr = proc.stderr.strip()
        if proc.returncode != 0 or not proc.stdout.strip():
            return [None] * n, stderr if stderr else "Unknown error"
        try:
            out = json.loads(proc.stdout.strip())
            if "error" in out:
                return [None] * n, out["error"]
            return out.get("times", [None] * n), ""
        except (json.JSONDecodeError, KeyError):
            return [None] * n, "Invalid JSON output from subprocess."