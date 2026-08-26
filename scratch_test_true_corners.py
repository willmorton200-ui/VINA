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

# 2. Extract Contour
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea)[:, 0, :].astype(np.float64) # (N, 2) [x, y]

# Find corners:
# P_TL: Top-Leftmost point (minimal x + y)
# P_TR: Top-Rightmost point (maximal x, minimal y)
# P_BL: Bottom-Left corner: The point where the left vertical wall meets the bottom curved arc!
# P_BR: Bottom-Right corner: The point where the right vertical wall meets the bottom curved arc!

# Let's find left wall points (points with x near the left silhouette)
y_min, y_max = np.min(cnt[:, 1]), np.max(cnt[:, 1])
x_min, x_max = np.min(cnt[:, 0]), np.max(cnt[:, 0])

# Corner selection:
# P_TL: contour point minimizing (x - x_min)/(x_max - x_min) + (y - y_min)/(y_max - y_min)
norm_x = (cnt[:, 0] - x_min) / max(x_max - x_min, 1.0)
norm_y = (cnt[:, 1] - y_min) / max(y_max - y_min, 1.0)

P_TL = cnt[np.argmin(norm_x + norm_y)]
P_TR = cnt[np.argmin((1.0 - norm_x) + norm_y)]

# For Bottom-Left corner P_BL:
# It is the point on the left side of the bottom arc (x in left 30% of width) that is furthest down along the left silhouette
# We want to find the corner where the vertical left edge turns into the bottom horizontal arc
left_bottom_candidates = cnt[(cnt[:, 0] <= x_min + 0.25 * (x_max - x_min)) & (cnt[:, 1] >= y_min + 0.70 * (y_max - y_min))]
# Corner is the point that maximizes (y - y_min) while keeping x minimal (i.e. maximizing y - 1.5*x)
P_BL = left_bottom_candidates[np.argmax(left_bottom_candidates[:, 1] - 1.8 * (left_bottom_candidates[:, 0] - x_min))]

right_bottom_candidates = cnt[(cnt[:, 0] >= x_max - 0.25 * (x_max - x_min)) & (cnt[:, 1] >= y_min + 0.70 * (y_max - y_min))]
P_BR = right_bottom_candidates[np.argmax(right_bottom_candidates[:, 1] - 1.8 * (x_max - right_bottom_candidates[:, 0]))]

print(f"Physical Corners:")
print(f"  P_TL: {P_TL}")
print(f"  P_TR: {P_TR}")
print(f"  P_BL: {P_BL}")
print(f"  P_BR: {P_BR}")

# 3. Fit Robust Bottom Curve between P_BL[0] and P_BR[0]
xs_bot = np.linspace(P_BL[0], P_BR[0], 60)
valid_xs_bot = []
raw_ys_bot = []

for x in xs_bot:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        valid_xs_bot.append(x)
        raw_ys_bot.append(float(np.max(col_ys)))

valid_xs_bot = np.array(valid_xs_bot)
raw_ys_bot = np.array(raw_ys_bot)

poly_bot = np.polyfit(valid_xs_bot, raw_ys_bot, deg=2)
for _ in range(5):
    fitted = np.polyval(poly_bot, valid_xs_bot)
    res = raw_ys_bot - fitted
    inliers = res <= np.median(res) + 3.0
    if np.sum(inliers) >= 10:
        poly_bot = np.polyfit(valid_xs_bot[inliers], raw_ys_bot[inliers], deg=2)

N_pts = 35
B_x = np.linspace(P_BL[0], P_BR[0], N_pts)
B_y = np.polyval(poly_bot, B_x)
B_y[0], B_y[-1] = P_BL[1], P_BR[1]

# 4. Fit Robust Top Curve between P_TL[0] and P_TR[0]
xs_top = np.linspace(P_TL[0], P_TR[0], 60)
valid_xs_top = []
raw_ys_top = []

for x in xs_top:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        valid_xs_top.append(x)
        raw_ys_top.append(float(np.min(col_ys)))

valid_xs_top = np.array(valid_xs_top)
raw_ys_top = np.array(raw_ys_top)

poly_top = np.polyfit(valid_xs_top, raw_ys_top, deg=2)
for _ in range(5):
    fitted = np.polyval(poly_top, valid_xs_top)
    res = fitted - raw_ys_top
    inliers = res <= np.median(res) + 3.0
    if np.sum(inliers) >= 10:
        poly_top = np.polyfit(valid_xs_top[inliers], raw_ys_top[inliers], deg=2)

T_x = np.linspace(P_TL[0], P_TR[0], N_pts)
T_y = np.polyval(poly_top, T_x)
T_y[0], T_y[-1] = P_TL[1], P_TR[1]

# 5. Render
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)

# Blue lateral lines connecting P_TL -> P_BL and P_TR -> P_BR
cv2.line(vis_overlay, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis_overlay, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green curves
cv2.polylines(vis_overlay, [np.column_stack((T_x, T_y)).astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [np.column_stack((B_x, B_y)).astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

h_vis, w_vis = vis_overlay.shape[:2]
zoom_bl = vis_overlay[int(h_vis*0.4):, :int(w_vis*0.6)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_true_corners_overlay.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_true_bl.png"), zoom_bl)

print("Saved barakiani_true_corners_overlay.png and zoom!")
