import cv2
import numpy as np

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
p1_res = p1.process(img_bgr)
mask = p1_res["mask"]
h, w = mask.shape[:2]

y_indices, x_indices = np.where(mask > 127)
valid_ys = np.unique(y_indices)
left_pts = []
right_pts = []
for y in valid_ys:
    col_xs = np.where(mask[y, :] > 127)[0]
    if len(col_xs) > 0:
        left_pts.append((float(col_xs[0]), float(y)))
        right_pts.append((float(col_xs[-1]), float(y)))

left_pts = np.array(left_pts)
right_pts = np.array(right_pts)

y_min, y_max = int(np.min(valid_ys)), int(np.max(valid_ys))
H_mask = y_max - y_min

# Find max width
widths = {int(y): right_pts[idx][0] - left_pts[idx][0] for idx, y in enumerate(valid_ys)}
max_w = max(widths.values())

# Bottom-left inflection
lower_left = left_pts[(left_pts[:, 1] >= y_min + 0.50 * H_mask) & (left_pts[:, 1] <= y_min + 0.90 * H_mask)]
y_bl_ref = float(lower_left[np.argmin(lower_left[:, 0] - 0.05 * lower_left[:, 1])][1])

# Bottom-right inflection: lowest y where width >= 0.70 * max_w
lower_br_candidates = [y for y in valid_ys if y >= y_min + 0.50 * H_mask and y <= y_min + 0.92 * H_mask and widths[y] >= 0.70 * max_w]
y_br_ref = float(max(lower_br_candidates)) if lower_br_candidates else float(y_max - 0.15 * H_mask)

print(f"y_bl_ref = {y_bl_ref:.1f}, y_br_ref = {y_br_ref:.1f}")
