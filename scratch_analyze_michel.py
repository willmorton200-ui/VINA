import cv2
import numpy as np

mask = cv2.imread("scratch_debug/michel_mask.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread("scratch_debug/michel_crop.png")
h, w = mask.shape[:2]

y_indices, x_indices = np.where(mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))

left_pts = []
right_pts = []
for y in range(y_min, y_max + 1):
    xs = np.where(mask[y, :] > 127)[0]
    if len(xs) > 0:
        left_pts.append((float(xs[0]), float(y)))
        right_pts.append((float(xs[-1]), float(y)))

left_pts = np.array(left_pts)
right_pts = np.array(right_pts)

print(f"y_min: {y_min}, y_max: {y_max}, total rows: {h}, total cols: {w}")
print(f"Top-most left_pts: {left_pts[:10]}")
print(f"Top-most right_pts: {right_pts[:10]}")
print(f"Bottom-most left_pts: {left_pts[-10:]}")
print(f"Bottom-most right_pts: {right_pts[-10:]}")

# Extreme points:
print(f"Absolute min x on mask: {np.min(x_indices)} at y={y_indices[np.argmin(x_indices)]}")
print(f"Absolute max x on mask: {np.max(x_indices)} at y={y_indices[np.argmax(x_indices)]}")
print(f"Absolute min y on mask: {y_min} at x={x_indices[np.argmin(y_indices)]}")
print(f"Absolute max y on mask: {y_max} at x={x_indices[np.argmax(y_indices)]}")
