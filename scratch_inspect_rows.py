import cv2
import numpy as np

mask = cv2.imread("scratch_debug/barakiani_raw_mask.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

y_indices, x_indices = np.where(mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))

# For each row y from y_min to y_max:
ys = np.arange(y_min, y_max + 1)
left_xs = []
right_xs = []

for y in ys:
    xs = np.where(mask[y, :] > 127)[0]
    if len(xs) > 0:
        left_xs.append((y, int(np.min(xs))))
        right_xs.append((y, int(np.max(xs))))

print(f"Row y={left_xs[0][0]} (Top): x_left={left_xs[0][1]}, x_right={right_xs[0][1]}")
print(f"Row y=200: x_left={left_xs[200 - y_min][1]}, x_right={right_xs[200 - y_min][1]}")
print(f"Row y=400: x_left={left_xs[400 - y_min][1]}, x_right={right_xs[400 - y_min][1]}")
print(f"Row y=600: x_left={left_xs[600 - y_min][1]}, x_right={right_xs[600 - y_min][1]}")
print(f"Row y=680: x_left={left_xs[680 - y_min][1]}, x_right={right_xs[680 - y_min][1]}")
print(f"Row y=720: x_left={left_xs[min(720 - y_min, len(left_xs)-1)][1]}, x_right={right_xs[min(720 - y_min, len(right_xs)-1)][1]}")
print(f"Row y={left_xs[-1][0]} (Bottom Apex): x_left={left_xs[-1][1]}, x_right={right_xs[-1][1]}")
