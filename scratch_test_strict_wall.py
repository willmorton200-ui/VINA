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
x_min, x_max = float(np.min(x_indices)), float(np.max(x_indices))
y_min, y_max = float(np.min(y_indices)), float(np.max(y_indices))

# 2. Extract Left and Right Lateral Profiles (Middle 60% of height where lateral edge is pure line)
y_mid_min = y_min + 0.15 * (y_max - y_min)
y_mid_max = y_max - 0.15 * (y_max - y_min)

left_wall_xs = []
left_wall_ys = []
right_wall_xs = []
right_wall_ys = []

for y in np.linspace(y_mid_min, y_mid_max, 50):
    y_int = int(round(y))
    col_xs = np.where(mask[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        left_wall_xs.append(float(col_xs[0]))
        left_wall_ys.append(y)
        right_wall_xs.append(float(col_xs[-1]))
        right_wall_ys.append(y)

# Fit linear lateral generators x = m*y + c
poly_left = np.polyfit(left_wall_ys, left_wall_xs, deg=1)
poly_right = np.polyfit(right_wall_ys, right_wall_xs, deg=1)

# Align to the outermost silhouette
min_left_x = np.min(left_wall_xs)
poly_left[1] = min_left_x - poly_left[0] * np.mean(left_wall_ys)

max_right_x = np.max(right_wall_xs)
poly_right[1] = max_right_x - poly_right[0] * np.mean(right_wall_ys)

# 3. Robust Column-wise Top and Bottom Profile Curves (Filter Outliers / Teeth)
xs = np.linspace(min_left_x, max_right_x, 80)
raw_tops = []
raw_bots = []
valid_xs = []

for x in xs:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        valid_xs.append(x)
        raw_tops.append(float(np.min(col_ys)))
        raw_bots.append(float(np.max(col_ys)))

valid_xs = np.array(valid_xs)
raw_tops = np.array(raw_tops)
raw_bots = np.array(raw_bots)

# Robust Top Fit
poly_top = np.polyfit(valid_xs, raw_tops, deg=2)
for _ in range(4):
    fitted = np.polyval(poly_top, valid_xs)
    res = fitted - raw_tops
    inliers = res <= np.median(res) + 3.5
    if np.sum(inliers) >= 10:
        poly_top = np.polyfit(valid_xs[inliers], raw_tops[inliers], deg=2)

# Robust Bottom Fit (Filters out teeth completely)
poly_bot = np.polyfit(valid_xs, raw_bots, deg=2)
for _ in range(4):
    fitted = np.polyval(poly_bot, valid_xs)
    res = raw_bots - fitted
    inliers = res <= np.median(res) + 3.5
    if np.sum(inliers) >= 10:
        poly_bot = np.polyfit(valid_xs[inliers], raw_bots[inliers], deg=2)

# 4. Exact Physical Corners: Where Left/Right Wall lines meet Top/Bottom curves
x_L = float(poly_left[1])
x_R = float(poly_right[1])

P_TL = np.array([x_L, float(np.polyval(poly_top, x_L))])
P_TR = np.array([x_R, float(np.polyval(poly_top, x_R))])
P_BL = np.array([x_L, float(np.polyval(poly_bot, x_L))])
P_BR = np.array([x_R, float(np.polyval(poly_bot, x_R))])

print("Physical Boundary Corners:")
print("  P_TL:", P_TL)
print("  P_TR:", P_TR)
print("  P_BL:", P_BL)
print("  P_BR:", P_BR)

# Generate Curves
N_pts = 35
T_x = np.linspace(P_TL[0], P_TR[0], N_pts)
T_y = np.polyval(poly_top, T_x)
T_y[0], T_y[-1] = P_TL[1], P_TR[1]

B_x = np.linspace(P_BL[0], P_BR[0], N_pts)
B_y = np.polyval(poly_bot, B_x)
B_y[0], B_y[-1] = P_BL[1], P_BR[1]

# 5. Render Comparison
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)

# Blue lateral lines STRICTLY on the outer physical wall
cv2.line(vis_overlay, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis_overlay, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green curves
cv2.polylines(vis_overlay, [np.column_stack((T_x, T_y)).astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [np.column_stack((B_x, B_y)).astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# Zoom in on bottom-left region
h_vis, w_vis = vis_overlay.shape[:2]
zoom_bl = vis_overlay[int(h_vis*0.4):, :int(w_vis*0.6)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_strict_wall_vector.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_strict_left.png"), zoom_bl)

print("Saved barakiani_strict_wall_vector.png and zoom!")
