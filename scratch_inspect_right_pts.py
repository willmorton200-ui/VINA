import cv2
import numpy as np

mask = cv2.imread("scratch_debug/liria_mask.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

y_indices, x_indices = np.where(mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))

right_pts = []
left_pts = []
for y in range(y_min, y_max + 1):
    xs = np.where(mask[y, :] > 127)[0]
    if len(xs) > 0:
        left_pts.append((xs[0], y))
        right_pts.append((xs[-1], y))

left_pts = np.array(left_pts)
right_pts = np.array(right_pts)

print("Right points near bottom:")
for pt in right_pts[-50:]:
    print(f"y={pt[1]}: x={pt[0]}")
