import cv2
import numpy as np
import os

mask = cv2.imread("scratch_debug/barakiani_raw_mask.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread("test_dataset/butilki/photo_2026-08-10_12-34-31.jpg") # We will crop it
h, w = mask.shape[:2]

# 1. Clean small noise
binary = np.uint8(mask > 127)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask = np.zeros_like(mask)
    clean_mask[labels == largest_label] = 255
    mask = clean_mask

# 2. Extract contour and 4 true corners strictly on side boundaries
y_indices, x_indices = np.where(mask > 127)
x_min, x_max = float(np.min(x_indices)), float(np.max(x_indices))
y_min, y_max = float(np.min(y_indices)), float(np.max(y_indices))

contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea)[:, 0, :].astype(np.float64) # (N, 2) [x, y]

# Extreme Quadrant Corner Selection (pinning strictly to left and right side boundaries)
norm_x = (cnt[:, 0] - x_min) / max(x_max - x_min, 1.0)
norm_y = (cnt[:, 1] - y_min) / max(y_max - y_min, 1.0)

score_TL = norm_x + norm_y
score_TR = (1.0 - norm_x) + norm_y
score_BL = norm_x + (1.0 - norm_y)
score_BR = (1.0 - norm_x) + (1.0 - norm_y)

P_TL = cnt[np.argmin(score_TL)]
P_TR = cnt[np.argmin(score_TR)]
P_BL = cnt[np.argmin(score_BL)]
P_BR = cnt[np.argmin(score_BR)]

print(f"Corners: P_TL={P_TL}, P_TR={P_TR}, P_BL={P_BL}, P_BR={P_BR}")

# 3. Robust Bottom Curve Fitting (Filtering Outliers / Teeth):
# Sample dense points along the bottom profile between P_BL[0] and P_BR[0]
xs_bot = np.linspace(P_BL[0], P_BR[0], 60)
raw_ys_bot = []
valid_xs_bot = []

for x in xs_bot:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        valid_xs_bot.append(x)
        raw_ys_bot.append(float(np.max(col_ys)))

valid_xs_bot = np.array(valid_xs_bot)
raw_ys_bot = np.array(raw_ys_bot)

# Robust Iterative Outlier Rejection (RANSAC / Huber-style):
# Initial fit
poly_bot = np.polyfit(valid_xs_bot, raw_ys_bot, deg=2)
# Refine by rejecting points protruding below the curve (teeth/spurs)
for _ in range(4):
    fitted_y = np.polyval(poly_bot, valid_xs_bot)
    residuals = raw_ys_bot - fitted_y
    # Bottom teeth stick OUTWARDS (positive residual for bottom curve, y > fitted_y)
    # Filter out points that protrude down more than threshold
    inlier_mask = residuals <= np.median(residuals) + 3.5
    if np.sum(inlier_mask) >= 10:
        poly_bot = np.polyfit(valid_xs_bot[inlier_mask], raw_ys_bot[inlier_mask], deg=2)

# Generate final smooth bottom curve
B_x = np.linspace(P_BL[0], P_BR[0], 35)
B_y = np.polyval(poly_bot, B_x)
B_y[0] = P_BL[1]
B_y[-1] = P_BR[1]

# 4. Robust Top Curve Fitting (Filtering Outliers / Nipples):
xs_top = np.linspace(P_TL[0], P_TR[0], 60)
raw_ys_top = []
valid_xs_top = []

for x in xs_top:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        valid_xs_top.append(x)
        raw_ys_top.append(float(np.min(col_ys)))

valid_xs_top = np.array(valid_xs_top)
raw_ys_top = np.array(raw_ys_top)

poly_top = np.polyfit(valid_xs_top, raw_ys_top, deg=2)
for _ in range(4):
    fitted_y = np.polyval(poly_top, valid_xs_top)
    residuals = fitted_y - raw_ys_top # Top nipples stick upwards (y < fitted_y)
    inlier_mask = residuals <= np.median(residuals) + 3.5
    if np.sum(inlier_mask) >= 10:
        poly_top = np.polyfit(valid_xs_top[inlier_mask], raw_ys_top[inlier_mask], deg=2)

T_x = np.linspace(P_TL[0], P_TR[0], 35)
T_y = np.polyval(poly_top, T_x)
T_y[0] = P_TL[1]
T_y[-1] = P_TR[1]

# 5. Render Comparison Overlay on Raw Mask and on Image
vis_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

# Draw Raw Mask with Greenish tint
green_layer = np.zeros_like(vis_mask)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis_mask, 0.60, green_layer, 0.40, 0)

# Lateral lines (Blue) strictly connecting side corners
cv2.line(vis_overlay, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis_overlay, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Smooth Guide Curves (Green) rejecting the teeth/spurs
cv2.polylines(vis_overlay, [np.column_stack((T_x, T_y)).astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [np.column_stack((B_x, B_y)).astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

# 4 Corner Green Dots
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
out_path = os.path.join(artifacts_dir, "barakiani_robust_curve_fitting.png")
cv2.imwrite(out_path, vis_overlay)
print(f"Saved {out_path} successfully!")
