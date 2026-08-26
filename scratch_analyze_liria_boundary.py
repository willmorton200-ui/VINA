import cv2
import numpy as np

mask = cv2.imread("scratch_debug/liria_mask.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread("scratch_debug/liria_crop.png")
h, w = mask.shape[:2]

y_indices, x_indices = np.where(mask > 127)
y_min = int(np.min(y_indices))
y_max = int(np.max(y_indices))

left_x = np.zeros(h, dtype=np.int32)
right_x = np.zeros(h, dtype=np.int32)
for y in range(y_min, y_max + 1):
    xs = np.where(mask[y, :] > 127)[0]
    if len(xs) > 0:
        left_x[y] = xs[0]
        right_x[y] = xs[-1]

print(f"y_min: {y_min}, y_max: {y_max}, total rows: {h}, total cols: {w}")
print(f"Left x at y_min ({y_min}): {left_x[y_min]}")
print(f"Left x at y={y_min+20}: {left_x[y_min+20]}")
print(f"Left x at y={y_min+100}: {left_x[y_min+100]}")
print(f"Left x at y={y_min+300}: {left_x[y_min+300]}")
print(f"Left x at y={y_max-100}: {left_x[y_max-100]}")
print(f"Left x at y={y_max-20}: {left_x[y_max-20]}")
print(f"Left x at y_max ({y_max}): {left_x[y_max]}")

# Find full contour
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea)[:, 0, :] # Shape (N, 2)
print(f"Contour points count: {len(cnt)}")

# Print extreme points of contour
top_pt = cnt[np.argmin(cnt[:, 1])]
bot_pt = cnt[np.argmax(cnt[:, 1])]
left_pt = cnt[np.argmin(cnt[:, 0])]
right_pt = cnt[np.argmax(cnt[:, 0])]
print(f"Extreme top point: {top_pt}")
print(f"Extreme bottom point: {bot_pt}")
print(f"Extreme left point: {left_pt}")
print(f"Extreme right point: {right_pt}")
