import cv2
import numpy as np

img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-29.jpg')
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

mask_full, _ = p1.sam_refiner.refine_mask(img, [479, 263, 960, 840])
crop = img[240:860, 460:960]
mask_c = mask_full[240:860, 460:960]

cnts, _ = cv2.findContours(np.uint8(mask_c > 127)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(cnts, key=cv2.contourArea).squeeze(1)

ys = cnt[:, 1]
xs = cnt[:, 0]
y_min, y_max = np.min(ys), np.max(ys)
x_min, x_max = np.min(xs), np.max(xs)
H_mask = y_max - y_min
W_mask = x_max - x_min

unique_ys = np.sort(np.unique(ys))
left_profile = []
for y_cur in unique_ys:
    min_x = float(np.min(cnt[cnt[:, 1] == y_cur, 0]))
    left_profile.append([min_x, float(y_cur)])
left_profile = np.array(left_profile)

# Left generator line from middle region
mid_L = (left_profile[:, 1] >= y_min + 0.20 * H_mask) & (left_profile[:, 1] <= y_min + 0.70 * H_mask)
poly_L = np.polyfit(left_profile[mid_L, 1], left_profile[mid_L, 0], deg=1)
print(f"poly_L: x = {poly_L[0]:.4f} * y + {poly_L[1]:.2f}")

# Check inliers in bottom half:
tol_L = max(5.0, 0.025 * W_mask)
dist_L = np.abs(left_profile[:, 0] - np.polyval(poly_L, left_profile[:, 1]))

# Inliers in bottom 50%
cand_bl = left_profile[(left_profile[:, 1] >= y_min + 0.50 * H_mask) & (dist_L <= tol_L)]
print("Bottom-most inliers on left generator:")
for p in cand_bl[-10:]:
    print(f"  pt = [{p[0]:.1f}, {p[1]:.1f}], dist_from_line = {abs(p[0] - np.polyval(poly_L, p[1])):.2f} px")

best_bl = cand_bl[np.argmax(cand_bl[:, 1])]
print(f"\nExact Lowest P_BL Corner: {best_bl}")
