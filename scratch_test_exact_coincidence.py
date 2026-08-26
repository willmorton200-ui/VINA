import cv2
import numpy as np
import os

mask = cv2.imread("scratch_debug/barakiani_raw_mask.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread("test_dataset/butilki/photo_2026-08-10_12-34-31.jpg")
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
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))

# 2. Extract Exact Row-by-Row Left and Right Contour Points
# For every row y, get the exact leftmost pixel (col_xs[0], y) and rightmost pixel (col_xs[-1], y)
valid_ys = np.unique(y_indices)
left_wall = []
right_wall = []

for y in valid_ys:
    col_xs = np.where(mask[y, :] > 127)[0]
    if len(col_xs) > 0:
        left_wall.append((float(col_xs[0]), float(y)))
        right_wall.append((float(col_xs[-1]), float(y)))

left_wall = np.array(left_wall)   # [x_left, y]
right_wall = np.array(right_wall) # [x_right, y]

# 3. Find Corner Inflection Points P_TL, P_TR, P_BL, P_BR along the true contour
# Along the left wall:
# P_TL is where x is near x_min and y is near y_min
left_top_idx = np.argmin((left_wall[:, 0] - x_min) + 1.2 * (left_wall[:, 1] - y_min))
P_TL = left_wall[left_top_idx]

# P_BL is the inflection point where the vertical left wall transitions into the bottom arc
# (the corner vertex on the left silhouette before the bottom arc curves inwards)
left_bot_candidates = left_wall[left_wall[:, 1] >= y_min + 0.65 * (y_max - y_min)]
# Inflection point: point minimizing curvature turning or maximizing distance from center line
left_bot_idx = np.argmin(left_bot_candidates[:, 0] + 0.15 * (y_max - left_bot_candidates[:, 1]))
P_BL = left_bot_candidates[left_bot_idx]

# Along the right wall:
right_top_idx = np.argmin((x_max - right_wall[:, 0]) + 1.2 * (right_wall[:, 1] - y_min))
P_TR = right_wall[right_top_idx]

right_bot_candidates = right_wall[right_wall[:, 1] >= y_min + 0.65 * (y_max - y_min)]
right_bot_idx = np.argmin((x_max - right_bot_candidates[:, 0]) + 0.15 * (y_max - right_bot_candidates[:, 1]))
P_BR = right_bot_candidates[right_bot_idx]

print(f"Physical Corners:")
print(f"  P_TL: {P_TL}")
print(f"  P_TR: {P_TR}")
print(f"  P_BL: {P_BL}")
print(f"  P_BR: {P_BR}")

# 4. Construct Lateral Side Profile Lines/Curves L(v) and R(v)
# L(v) extracts the exact mask boundary points between P_TL[1] and P_BL[1]
y_L_range = np.linspace(P_TL[1], P_BL[1], 40)
L_pts = []
for y in y_L_range:
    y_int = int(np.clip(round(y), 0, h - 1))
    col_xs = np.where(mask[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        L_pts.append((float(col_xs[0]), y))
    else:
        L_pts.append((P_TL[0], y))
L_curve = np.array(L_pts)

# R(v) extracts the exact mask boundary points between P_TR[1] and P_BR[1]
y_R_range = np.linspace(P_TR[1], P_BR[1], 40)
R_pts = []
for y in y_R_range:
    y_int = int(np.clip(round(y), 0, h - 1))
    col_xs = np.where(mask[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        R_pts.append((float(col_xs[-1]), y))
    else:
        R_pts.append((P_TR[0], y))
R_curve = np.array(R_pts)

# 5. Robust Bottom Curve between P_BL and P_BR (Rejecting Teeth/Spurs)
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
B_curve = np.column_stack((B_x, B_y))

# 6. Robust Top Curve between P_TL and P_TR
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
T_curve = np.column_stack((T_x, T_y))

# 7. Render Visual
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)

# Blue lateral lines/polylines STRICTLY ON THE MASK BOUNDARY
cv2.polylines(vis_overlay, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Green curves
cv2.polylines(vis_overlay, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

h_vis, w_vis = vis_overlay.shape[:2]
zoom_bl = vis_overlay[int(h_vis*0.4):, :int(w_vis*0.6)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_boundary_perfect_overlay.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_boundary_perfect.png"), zoom_bl)

print("Saved barakiani_boundary_perfect_overlay.png and zoom!")
