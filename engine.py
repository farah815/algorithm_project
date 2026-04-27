import time

class Engine:
    def run_code(self, user_code: str, arr: list, runs: int = 5) -> float:
        local_env = {}
        try:
            exec(user_code, {}, local_env)
            func = list(local_env.values())[0]
            total_time = 0
            
            for i in range(runs):
                start = time.perf_counter()
                func(arr)
                end = time.perf_counter()
                total_time += (end - start)
                
            return (total_time / runs) * 1000
        
        except Exception as e:
            print(f"Error: {e}")
            return -1  