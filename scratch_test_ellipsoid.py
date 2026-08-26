import cv2
import numpy as np
import os

crop = cv2.imread(r"D:\VINA\outputs\test_barakiani_pruned_smooth\photo_2026-08-10_12-34-31\stage1_retinex.png")
mask = cv2.imread(r"D:\VINA\outputs\test_barakiani_pruned_smooth\photo_2026-08-10_12-34-31\stage1_mask.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

# 1. Clean to single largest component
binary = np.uint8(mask > 127)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask = np.zeros_like(mask)
    clean_mask[labels == largest_label] = 255
    mask = clean_mask

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

y_indices, x_indices = np.where(mask_closed > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))

# Extract side walls
valid_ys = np.unique(y_indices)
left_wall = []
right_wall = []
for y in valid_ys:
    col_xs = np.where(mask_closed[y, :] > 127)[0]
    if len(col_xs) > 0:
        left_wall.append((float(col_xs[0]), float(y)))
        right_wall.append((float(col_xs[-1]), float(y)))

left_wall = np.array(left_wall)
right_wall = np.array(right_wall)

# Corners on exact mask perimeter
left_top_idx = np.argmin((left_wall[:, 0] - x_min) + 1.2 * (left_wall[:, 1] - y_min))
P_TL = left_wall[left_top_idx]

left_bot_candidates = left_wall[left_wall[:, 1] >= y_min + 0.65 * (y_max - y_min)]
left_bot_idx = np.argmin(left_bot_candidates[:, 0] + 0.15 * (y_max - left_bot_candidates[:, 1]))
P_BL = left_bot_candidates[left_bot_idx]

right_top_idx = np.argmin((x_max - right_wall[:, 0]) + 1.2 * (right_wall[:, 1] - y_min))
P_TR = right_wall[right_top_idx]

right_bot_candidates = right_wall[right_wall[:, 1] >= y_min + 0.65 * (y_max - y_min)]
right_bot_idx = np.argmin((x_max - right_bot_candidates[:, 0]) + 0.15 * (y_max - right_bot_candidates[:, 1]))
P_BR = right_bot_candidates[right_bot_idx]

# Lateral polylines
N_pts = 50
ys_left = np.linspace(P_TL[1], P_BL[1], N_pts)
L_pts = []
for y in ys_left:
    y_int = int(np.clip(round(y), 0, h - 1))
    col_xs = np.where(mask_closed[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        L_pts.append((float(col_xs[0]), y))
    else:
        L_pts.append((P_TL[0], y))
L_curve = np.array(L_pts)
L_curve[:, 0] = cv2.GaussianBlur(L_curve[:, 0].reshape(-1, 1), (5, 1), 1.0).ravel()
L_curve[0], L_curve[-1] = P_TL, P_BL

ys_right = np.linspace(P_TR[1], P_BR[1], N_pts)
R_pts = []
for y in ys_right:
    y_int = int(np.clip(round(y), 0, h - 1))
    col_xs = np.where(mask_closed[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        R_pts.append((float(col_xs[-1]), y))
    else:
        R_pts.append((P_TR[0], y))
R_curve = np.array(R_pts)
R_curve[:, 0] = cv2.GaussianBlur(R_curve[:, 0].reshape(-1, 1), (5, 1), 1.0).ravel()
R_curve[0], R_curve[-1] = P_TR, P_BR

# 2. Extract Bottom Profile to find apex and fit true semi-ellipse
xs_bot = np.linspace(P_BL[0], P_BR[0], N_pts)
raw_ys_bot = []
for x in xs_bot:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask_closed[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_bot.append(float(np.max(col_ys)))
    else:
        raw_ys_bot.append(P_BL[1])
raw_ys_bot = np.array(raw_ys_bot)

# Robust apex detection (median of central 20% points)
mid_idx = len(raw_ys_bot) // 2
mid_span = int(len(raw_ys_bot) * 0.15)
y_apex_bot = float(np.median(raw_ys_bot[mid_idx - mid_span : mid_idx + mid_span]))

# True Semi-Ellipse Formulation:
# Parametric angle theta from 0 to pi (or -pi/2 to pi/2)
# Major axis a: half width
x0_bot = (P_BL[0] + P_BR[0]) / 2.0
a_bot = (P_BR[0] - P_BL[0]) / 2.0
# Corner average height
y_corner_avg_bot = (P_BL[1] + P_BR[1]) / 2.0
b_bot = max(y_apex_bot - y_corner_avg_bot, 5.0)

# Generate true semi-ellipse points:
# x(theta) = x0 - a * cos(theta) for theta in [0, pi]
# y(theta) = y_corner_avg + b * sin(theta) + linear tilt
theta = np.linspace(0, np.pi, N_pts)
B_ell_x = x0_bot - a_bot * np.cos(theta)
# Pure ellipse sagitta:
sagitta_bot = b_bot * np.sin(theta)
# Linear tilt between P_BL and P_BR:
tilt_bot = (1.0 - theta / np.pi) * P_BL[1] + (theta / np.pi) * P_BR[1] - y_corner_avg_bot
B_ell_y = y_corner_avg_bot + sagitta_bot + tilt_bot
B_ell_y[0] = P_BL[1]
B_ell_y[-1] = P_BR[1]
B_curve_ellipse = np.column_stack((B_ell_x, B_ell_y))

# Top Semi-Ellipse:
xs_top = np.linspace(P_TL[0], P_TR[0], N_pts)
raw_ys_top = []
for x in xs_top:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask_closed[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_top.append(float(np.min(col_ys)))
    else:
        raw_ys_top.append(P_TL[1])
raw_ys_top = np.array(raw_ys_top)

y_apex_top = float(np.median(raw_ys_top[mid_idx - mid_span : mid_idx + mid_span]))
x0_top = (P_TL[0] + P_TR[0]) / 2.0
a_top = (P_TR[0] - P_TL[0]) / 2.0
y_corner_avg_top = (P_TL[1] + P_TR[1]) / 2.0
b_top = max(y_corner_avg_top - y_apex_top, 5.0)

T_ell_x = x0_top - a_top * np.cos(theta)
sagitta_top = -b_top * np.sin(theta)
tilt_top = (1.0 - theta / np.pi) * P_TL[1] + (theta / np.pi) * P_TR[1] - y_corner_avg_top
T_ell_y = y_corner_avg_top + sagitta_top + tilt_top
T_ell_y[0] = P_TL[1]
T_ell_y[-1] = P_TR[1]
T_curve_ellipse = np.column_stack((T_ell_x, T_ell_y))

# 3. Render Visual Comparison
vis = crop.copy()
mask_2d = mask > 127
green_layer = crop.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Blue lateral polylines
cv2.polylines(vis, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Ellipsoid Green Curves
cv2.polylines(vis, [T_curve_ellipse.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [B_curve_ellipse.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

h_v, w_v = vis.shape[:2]
zoom_bl = vis[int(h_v*0.35):, :int(w_v*0.75)].copy()

# Also build and draw Coon's patch grid overlay with ellipsoid guides!
u_vals = np.linspace(0.0, 1.0, 31)
v_vals = np.linspace(0.0, 1.0, 31)
idx_orig = np.linspace(0.0, 1.0, N_pts)

T_resamp = np.column_stack((np.interp(u_vals, idx_orig, T_curve_ellipse[:, 0]), np.interp(u_vals, idx_orig, T_curve_ellipse[:, 1])))
B_resamp = np.column_stack((np.interp(u_vals, idx_orig, B_curve_ellipse[:, 0]), np.interp(u_vals, idx_orig, B_curve_ellipse[:, 1])))
L_resamp = np.column_stack((np.interp(v_vals, idx_orig, L_curve[:, 0]), np.interp(v_vals, idx_orig, L_curve[:, 1])))
R_resamp = np.column_stack((np.interp(v_vals, idx_orig, R_curve[:, 0]), np.interp(v_vals, idx_orig, R_curve[:, 1])))

u_grid = np.zeros((31, 31), dtype=np.float32)
v_grid = np.zeros((31, 31), dtype=np.float32)
for i in range(31):
    v = v_vals[i]
    for j in range(31):
        u = u_vals[j]
        corner_blend = (1.0 - u) * (1.0 - v) * P_TL + u * (1.0 - v) * P_TR + (1.0 - u) * v * P_BL + u * v * P_BR
        pt = (1.0 - v) * T_resamp[j] + v * B_resamp[j] + (1.0 - u) * L_resamp[i] + u * R_resamp[i] - corner_blend
        u_grid[i, j] = pt[0]
        v_grid[i, j] = pt[1]

vis_mesh = crop.copy()
# Draw Blue Lateral
cv2.polylines(vis_mesh, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_mesh, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
# Draw Grid
for i in range(31):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 255, 0) if (i == 0 or i == 30) else (0, 240, 255)
    thick = 3 if (i == 0 or i == 30) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, cv2.LINE_AA)
for j in range(31):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    cv2.polylines(vis_mesh, [pts], False, (0, 240, 255), 1, cv2.LINE_AA)
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

zoom_mesh = vis_mesh[int(h_v*0.35):, :int(w_v*0.75)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_ellipsoid_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_ellipsoid.png"), zoom_bl)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_ellipsoid_mesh.png"), vis_mesh)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_ellipsoid_mesh.png"), zoom_mesh)

print("Saved barakiani_ellipsoid_overlay.png, mesh, and zoom successfully!")
