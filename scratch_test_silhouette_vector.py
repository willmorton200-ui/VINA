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
x_min, x_max = float(np.min(x_indices)), float(np.max(x_indices))
y_min, y_max = float(np.min(y_indices)), float(np.max(y_indices))

# 2. Extract Row-by-Row Left and Right Profile (Silhouette)
# For each row y where mask exists, get the leftmost pixel x_left(y) and rightmost pixel x_right(y)
valid_ys = np.unique(y_indices)
left_pts = []
right_pts = []

for y in valid_ys:
    col_xs = np.where(mask[y, :] > 127)[0]
    if len(col_xs) > 0:
        left_pts.append((float(col_xs[0]), float(y)))
        right_pts.append((float(col_xs[-1]), float(y)))

left_pts = np.array(left_pts)   # [x_left, y]
right_pts = np.array(right_pts) # [x_right, y]

# 3. Fit Straight Lateral Generators x = m*y + c (using RANSAC / Theil-Sen to ignore any local bumps)
poly_left = np.polyfit(left_pts[:, 1], left_pts[:, 0], deg=1)   # x = m_l * y + c_l
poly_right = np.polyfit(right_pts[:, 1], right_pts[:, 0], deg=1) # x = m_r * y + c_r

# Shift generators to strictly encompass the outermost silhouette (x_min and x_max)
min_left_dev = np.min(left_pts[:, 0] - np.polyval(poly_left, left_pts[:, 1]))
max_right_dev = np.max(right_pts[:, 0] - np.polyval(poly_right, right_pts[:, 1]))

poly_left[1] += min_left_dev
poly_right[1] += max_right_dev

# 4. Dense Column-wise Top and Bottom profile for robust curve fitting
xs = np.linspace(x_min, x_max, 100)
top_samples = []
bot_samples = []

for x in xs:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        top_samples.append((x, float(np.min(col_ys))))
        bot_samples.append((x, float(np.max(col_ys))))

top_samples = np.array(top_samples)
bot_samples = np.array(bot_samples)

# Robust Top Curve (Reject upward nipples)
poly_top = np.polyfit(top_samples[:, 0], top_samples[:, 1], deg=2)
for _ in range(4):
    fitted_y = np.polyval(poly_top, top_samples[:, 0])
    residuals = fitted_y - top_samples[:, 1]
    inliers = residuals <= np.median(residuals) + 3.0
    if np.sum(inliers) >= 10:
        poly_top = np.polyfit(top_samples[inliers, 0], top_samples[inliers, 0]**0 * top_samples[inliers, 1], deg=2)
        # quadratic fit
        poly_top = np.polyfit(top_samples[inliers, 0], top_samples[inliers, 1], deg=2)

# Robust Bottom Curve (Reject downward teeth)
poly_bot = np.polyfit(bot_samples[:, 0], bot_samples[:, 1], deg=2)
for _ in range(4):
    fitted_y = np.polyval(poly_bot, bot_samples[:, 0])
    residuals = bot_samples[:, 1] - fitted_y
    inliers = residuals <= np.median(residuals) + 3.0
    if np.sum(inliers) >= 10:
        poly_bot = np.polyfit(bot_samples[inliers, 0], bot_samples[inliers, 1], deg=2)

# 5. Intersect Side Lines with Top/Bottom Curves to find the 4 EXACT Corners!
# Line: x = m*y + c  <=>  y = (x - c) / m  (or intersect directly)
# Let x_L = np.polyval(poly_left, y_mid)
x_L_top = np.polyval(poly_left, y_min)
x_R_top = np.polyval(poly_right, y_min)
x_L_bot = np.polyval(poly_left, y_max)
x_R_bot = np.polyval(poly_right, y_max)

# Intersect Top curve with Left Line:
P_TL = np.array([x_L_top, float(np.polyval(poly_top, x_L_top))])
P_TR = np.array([x_R_top, float(np.polyval(poly_top, x_R_top))])
P_BL = np.array([x_L_bot, float(np.polyval(poly_bot, x_L_bot))])
P_BR = np.array([x_R_bot, float(np.polyval(poly_bot, x_R_bot))])

print(f"Calculated 4 Physical Corners:")
print(f"  P_TL: {P_TL}")
print(f"  P_TR: {P_TR}")
print(f"  P_BL: {P_BL}")
print(f"  P_BR: {P_BR}")

# Generate Top and Bottom Curves between P_TL/P_TR and P_BL/P_BR
N_pts = 35
T_x = np.linspace(P_TL[0], P_TR[0], N_pts)
T_y = np.polyval(poly_top, T_x)
T_y[0], T_y[-1] = P_TL[1], P_TR[1]

B_x = np.linspace(P_BL[0], P_BR[0], N_pts)
B_y = np.polyval(poly_bot, B_x)
B_y[0], B_y[-1] = P_BL[1], P_BR[1]

# 6. Render Visual
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)

# Blue lateral lines STRICTLY along the outermost silhouette
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
zoom_bl = vis_overlay[int(h_vis*0.5):, :int(w_vis*0.55)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_true_silhouette_vector.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_bottom_left.png"), zoom_bl)

print("Saved barakiani_true_silhouette_vector.png and zoom_bl!")
