import cv2
import numpy as np

mask = cv2.imread("scratch_debug/barakiani_raw_mask.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

y_indices, x_indices = np.where(mask > 127)
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))

# For each x in [x_min, x_max], print max_y
print(f"X range: [{x_min}, {x_max}]")
for x in [35, 50, 75, 100, 150, 200, 250, 300, 350, 400, 430, 455]:
    ys = np.where(mask[:, x] > 127)[0]
    print(f"x={x:3d} -> min_y={np.min(ys):3d}, max_y={np.max(ys):3d}")
