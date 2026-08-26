import cv2
import numpy as np
import os

mask = cv2.imread("scratch_debug/barakiani_raw_mask.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

# 1. Clean to single largest component
binary = np.uint8(mask > 127)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask = np.zeros_like(mask)
    clean_mask[labels == largest_label] = 255
    mask = clean_mask

y_indices, x_indices = np.where(mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))

# 2. Extract row-by-row leftmost and rightmost profile points
valid_ys = np.unique(y_indices)
left_profile = []
right_profile = []

for y in valid_ys:
    col_xs = np.where(mask[y, :] > 127)[0]
    if len(col_xs) > 0:
        left_profile.append((float(col_xs[0]), float(y)))
        right_profile.append((float(col_xs[-1]), float(y)))

left_profile = np.array(left_profile)   # (x, y)
right_profile = np.array(right_profile) # (x, y)

# 3. Fit straight lateral lines x = m*y + c along the physical left & right silhouettes
# Take the middle 70% of rows where the lateral edges are straight
y_span = y_max - y_min
y_h1 = y_min + 0.10 * y_span
y_h2 = y_max - 0.15 * y_span

left_mid = left_profile[(left_profile[:, 1] >= y_h1) & (left_profile[:, 1] <= y_h2)]
right_mid = right_profile[(right_profile[:, 1] >= y_h1) & (right_profile[:, 1] <= y_h2)]

# Robust linear fit (Theil-Sen / Huber)
poly_left = np.polyfit(left_mid[:, 1], left_mid[:, 0], deg=1)    # x = poly_left[0]*y + poly_left[1]
poly_right = np.polyfit(right_mid[:, 1], right_mid[:, 0], deg=1) # x = poly_right[0]*y + poly_right[1]

# Align strictly to outermost contour (minimum left x, maximum right x)
poly_left[1] += np.percentile(left_mid[:, 0] - np.polyval(poly_left, left_mid[:, 1]), 5)
poly_right[1] += np.percentile(right_mid[:, 0] - np.polyval(poly_right, right_mid[:, 1]), 95)

# 4. Dense Column-wise Top and Bottom Profile for Robust Curve Fitting
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))
xs_dense = np.linspace(x_min, x_max, 80)
raw_bots = []
raw_tops = []
valid_xs = []

for x in xs_dense:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        valid_xs.append(x)
        raw_tops.append(float(np.min(col_ys)))
        raw_bots.append(float(np.max(col_ys)))

valid_xs = np.array(valid_xs)
raw_tops = np.array(raw_tops)
raw_bots = np.array(raw_bots)

# Robust Bottom Curve: Reject downward-protruding teeth (residuals > threshold)
poly_bot = np.polyfit(valid_xs, raw_bots, deg=2)
for _ in range(5):
    fitted = np.polyval(poly_bot, valid_xs)
    res = raw_bots - fitted
    # Teeth protrude below the curve (positive residual)
    inliers = res <= np.median(res) + 3.0
    if np.sum(inliers) >= 12:
        poly_bot = np.polyfit(valid_xs[inliers], raw_bots[inliers], deg=2)

# Robust Top Curve: Reject upward nipples
poly_top = np.polyfit(valid_xs, raw_tops, deg=2)
for _ in range(5):
    fitted = np.polyval(poly_top, valid_xs)
    res = fitted - raw_tops
    inliers = res <= np.median(res) + 3.0
    if np.sum(inliers) >= 12:
        poly_top = np.polyfit(valid_xs[inliers], raw_tops[inliers], deg=2)

# 5. Exact Physical Corners: Where Left/Right Silhouette lines meet the Bottom/Top curves!
# Top corners:
# For left side at top: y is near y_min
y_T_left = float(np.polyval(poly_top, np.polyval(poly_left, y_min)))
x_T_left = float(np.polyval(poly_left, y_T_left))
P_TL = np.array([x_T_left, y_T_left])

y_T_right = float(np.polyval(poly_top, np.polyval(poly_right, y_min)))
x_T_right = float(np.polyval(poly_right, y_T_right))
P_TR = np.array([x_T_right, y_T_right])

# Bottom corners: Where lateral lines intersect the bottom curve!
# Intersection: y = a*x^2 + b*x + c and x = m*y + k
# x_B_left is at the base of left profile
y_B_left_init = np.percentile(left_mid[:, 1], 98) + 0.10 * y_span
x_B_left = float(np.polyval(poly_left, y_B_left_init))
y_B_left = float(np.polyval(poly_bot, x_B_left))
# One Newton step to exact intersection
x_B_left = float(np.polyval(poly_left, y_B_left))
P_BL = np.array([x_B_left, y_B_left])

y_B_right_init = np.percentile(right_mid[:, 1], 98) + 0.10 * y_span
x_B_right = float(np.polyval(poly_right, y_B_right_init))
y_B_right = float(np.polyval(poly_bot, x_B_right))
x_B_right = float(np.polyval(poly_right, y_B_right))
P_BR = np.array([x_B_right, y_B_right])

print("Physical Boundary Corners (Strict Silhouette Attachment):")
print("  P_TL:", P_TL)
print("  P_TR:", P_TR)
print("  P_BL:", P_BL)
print("  P_BR:", P_BR)

# Generate smooth curves anchored at corners
N_pts = 35
T_x = np.linspace(P_TL[0], P_TR[0], N_pts)
T_y = np.polyval(poly_top, T_x)
T_y[0], T_y[-1] = P_TL[1], P_TR[1]

B_x = np.linspace(P_BL[0], P_BR[0], N_pts)
B_y = np.polyval(poly_bot, B_x)
B_y[0], B_y[-1] = P_BL[1], P_BR[1]

# 6. Render Overlay
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)

# Blue lateral lines strictly along the left & right silhouette
cv2.line(vis_overlay, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis_overlay, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green curves
cv2.polylines(vis_overlay, [np.column_stack((T_x, T_y)).astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [np.column_stack((B_x, B_y)).astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# Zoom in on bottom-left region to match user's screenshot
h_vis, w_vis = vis_overlay.shape[:2]
zoom_bl = vis_overlay[int(h_vis*0.4):, :int(w_vis*0.6)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_strict_silhouette_overlay.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_strict_silhouette.png"), zoom_bl)

print("Saved barakiani_strict_silhouette_overlay.png and zoom!")
