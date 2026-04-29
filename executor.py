import subprocess
import sys
import tempfile
import os
import json
import statistics

class SafeExecutor:
    @staticmethod
    def run(user_code: str, data: list, timeout_sec: float = 10.0, runs: int = 5) -> tuple[float | None, object]:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            script_path = f.name
            f.write(f"""
import sys, json, time, statistics

user_code = {json.dumps(user_code)}
original_data = {json.dumps(data)}
runs = {runs}

exec(user_code)

func = None
for name, obj in list(locals().items()):
    if callable(obj) and name not in ('exec', 'locals', 'globals'):
        func = obj
        break

if func is None:
    print(json.dumps({{"error": "No callable function found"}}))
    sys.exit(1)

# Warmup (discard)
func(list(original_data))

samples = []
for _ in range(runs):
    # Fresh copy for each run to avoid mutation
    data_copy = list(original_data)
    start = time.perf_counter()
    result = func(data_copy)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    samples.append(elapsed_ms)

median_ms = statistics.median(samples)
print(json.dumps({{"time_ms": median_ms, "result": str(result)}}))
""")
        try:
            process = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=timeout_sec)
            if process.returncode != 0:
                return None, None
            out = json.loads(process.stdout.strip())
            if "error" in out:
                return None, None
            return out["time_ms"], out["result"]
        except Exception:
            return None, None
        finally:
            try:
                os.unlink(script_path)
            except:
                pass