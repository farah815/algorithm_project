import numpy as np

# Calibrate exact slope threshold for O(n²) vs O(n²logn)
# across different size ranges used in practice

print('Slope calibration for O(n² log n):')
for sizes in [[50,100,200,400,800,1200,1600,2000],[50,100,200,400,800,1200],[20,50,100,200]]:
    n = np.array(sizes, dtype=float)
    t = n**2 * np.log2(n)
    s = np.polyfit(np.log(n), np.log(t), 1)[0]
    print(f'  sizes {sizes[0]}-{sizes[-1]}: slope={s:.4f}')

print()
print('Slope calibration for pure O(n²):')
for sizes in [[50,100,200,400,800,1200,1600,2000],[50,100,200,400,800,1200]]:
    n = np.array(sizes, dtype=float)
    t = n**2
    s = np.polyfit(np.log(n), np.log(t), 1)[0]
    print(f'  sizes {sizes[0]}-{sizes[-1]}: slope={s:.4f}')

print()
print('Safe cutoff: slope > 2.08 → O(n² log n)  (gap from 2.0 is > any realistic noise)')

# Same for O(n) vs O(n log n)
print()
print('Slope calibration for O(n log n):')
sizes = [50,100,200,400,800,1200,1600,2000]
n = np.array(sizes, dtype=float)
t = n * np.log2(n)
s = np.polyfit(np.log(n), np.log(t), 1)[0]
print(f'  slope = {s:.4f}')
print(f'  Safe cutoff: slope > 1.06 → O(n log n)')