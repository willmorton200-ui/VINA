import cv2
import numpy as np
import os

mask = cv2.imread("scratch_debug/barakiani_raw_mask.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

y_indices, x_indices = np.where(mask > 127)
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))

# 1. Fit Left and Right Physical Wall Lines (using rows where edge is straight)
# For left wall: rows from y_min + 0.15*H to y_min + 0.65*H
H = y_max - y_min
left_wall_pts = []
right_wall_pts = []

for y in range(int(y_min + 0.15 * H), int(y_min + 0.65 * H), 2):
    row_xs = np.where(mask[y, :] > 127)[0]
    if len(row_xs) > 0:
        left_wall_pts.append((row_xs[0], y))
        right_wall_pts.append((row_xs[-1], y))

left_wall_pts = np.array(left_wall_pts)
right_wall_pts = np.array(right_wall_pts)

# Fit line x = m*y + c
poly_left_line = np.polyfit(left_wall_pts[:, 1], left_wall_pts[:, 0], deg=1)
poly_right_line = np.polyfit(right_wall_pts[:, 1], right_wall_pts[:, 0], deg=1)

# Align line to the outermost edge (min x on left, max x on right)
poly_left_line[1] = np.percentile(left_wall_pts[:, 0] - poly_left_line[0] * left_wall_pts[:, 1], 5)
poly_right_line[1] = np.percentile(right_wall_pts[:, 0] - poly_right_line[0] * right_wall_pts[:, 1], 95)

# 2. Sample bottom profile in the central 70% of the cylinder to fit clean smooth bottom ellipse/arc
xs_sample = np.linspace(x_min + 0.15 * (x_max - x_min), x_max - 0.15 * (x_max - x_min), 60)
raw_bots = []
valid_xs = []

for x in xs_sample:
    x_int = int(round(x))
    ys = np.where(mask[:, x_int] > 127)[0]
    if len(ys) > 0:
        valid_xs.append(x)
        raw_bots.append(float(np.max(ys)))

valid_xs = np.array(valid_xs)
raw_bots = np.array(raw_bots)

# Robust quadratic fit (filters out bottom teeth/spurs)
poly_bot = np.polyfit(valid_xs, raw_bots, deg=2)
for _ in range(5):
    fitted = np.polyval(poly_bot, valid_xs)
    res = raw_bots - fitted
    inliers = res <= np.median(res) + 2.5
    if np.sum(inliers) >= 10:
        poly_bot = np.polyfit(valid_xs[inliers], raw_bots[inliers], deg=2)

# Sample top profile
raw_tops = []
valid_tops_xs = []
for x in xs_sample:
    x_int = int(round(x))
    ys = np.where(mask[:, x_int] > 127)[0]
    if len(ys) > 0:
        valid_tops_xs.append(x)
        raw_tops.append(float(np.min(ys)))

valid_tops_xs = np.array(valid_tops_xs)
raw_tops = np.array(raw_tops)
poly_top = np.polyfit(valid_tops_xs, raw_tops, deg=2)
for _ in range(5):
    fitted = np.polyval(poly_top, valid_tops_xs)
    res = fitted - raw_tops
    inliers = res <= np.median(res) + 2.5
    if np.sum(inliers) >= 10:
        poly_top = np.polyfit(valid_tops_xs[inliers], raw_tops[inliers], deg=2)

# 3. Intersect Left/Right Wall Lines with Top/Bottom Curves:
# For bottom-left corner P_BL:
# Left line is x = m*y + c. Solve for y on parabola y = a*x^2 + b*x + c
# Parabola at x_left:
x_BL_est = np.polyval(poly_left_line, y_max - 0.15 * H)
y_BL = float(np.polyval(poly_bot, x_BL_est))
x_BL = float(np.polyval(poly_left_line, y_BL))
P_BL = np.array([x_BL, y_BL])

x_BR_est = np.polyval(poly_right_line, y_max - 0.15 * H)
y_BR = float(np.polyval(poly_bot, x_BR_est))
x_BR = float(np.polyval(poly_right_line, y_BR))
P_BR = np.array([x_BR, y_BR])

# Top corners:
x_TL_est = np.polyval(poly_left_line, y_min + 0.10 * H)
y_TL = float(np.polyval(poly_top, x_TL_est))
x_TL = float(np.polyval(poly_left_line, y_TL))
P_TL = np.array([x_TL, y_TL])

x_TR_est = np.polyval(poly_right_line, y_min + 0.10 * H)
y_TR = float(np.polyval(poly_top, x_TR_est))
x_TR = float(np.polyval(poly_right_line, y_TR))
P_TR = np.array([x_TR, y_TR])

print("Strict Silhouette Wall Corners:")
print("  P_TL:", P_TL)
print("  P_TR:", P_TR)
print("  P_BL:", P_BL)
print("  P_BR:", P_BR)

# Generate smooth curves between P_TL/P_TR and P_BL/P_BR
N_pts = 35
T_x = np.linspace(P_TL[0], P_TR[0], N_pts)
T_y = np.polyval(poly_top, T_x)
T_y[0], T_y[-1] = P_TL[1], P_TR[1]

B_x = np.linspace(P_BL[0], P_BR[0], N_pts)
B_y = np.polyval(poly_bot, B_x)
B_y[0], B_y[-1] = P_BL[1], P_BR[1]

# 4. Render Visual
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)

# Blue lateral lines connecting P_TL -> P_BL and P_TR -> P_BR strictly along the outer silhouette
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
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_strict_wall_overlay.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_strict_wall.png"), zoom_bl)

print("Saved barakiani_strict_wall_overlay.png and zoom!")
