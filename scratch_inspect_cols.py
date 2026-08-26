import cv2
import numpy as np

mask = cv2.imread("scratch_debug/barakiani_raw_mask.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

y_indices, x_indices = np.where(mask > 127)
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))

# For each column x from x_min to x_max, find min_y and max_y
xs = np.arange(x_min, x_max + 1)
min_ys = []
max_ys = []

for x in xs:
    ys = np.where(mask[:, x] > 127)[0]
    min_ys.append(int(np.min(ys)))
    max_ys.append(int(np.max(ys)))

min_ys = np.array(min_ys)
max_ys = np.array(max_ys)

print(f"Mask X range: [{x_min}, {x_max}] (width = {x_max - x_min + 1})")
print(f"Leftmost column (x={x_min}): top_y={min_ys[0]}, bot_y={max_ys[0]}")
print(f"Rightmost column (x={x_max}): top_y={min_ys[-1]}, bot_y={max_ys[-1]}")
print(f"Center column (x={xs[len(xs)//2]}): top_y={min_ys[len(xs)//2]}, bot_y={max_ys[len(xs)//2]}")
