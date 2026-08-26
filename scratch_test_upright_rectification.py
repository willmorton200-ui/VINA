import cv2
import numpy as np
import os

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-31.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

# 1. Segment using Stage 1
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
ch, cw = crop_bgr.shape[:2]

# Clean mask
binary = np.uint8(crop_mask > 127)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask = np.zeros_like(crop_mask)
    clean_mask[labels == largest_label] = 255
    crop_mask = clean_mask

# 2. Step 1: Determine Lateral Boundaries of the Mask
y_indices, x_indices = np.where(crop_mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))
H = y_max - y_min

valid_ys = np.unique(y_indices)
left_wall_pts = []
right_wall_pts = []

for y in valid_ys:
    if y_min + 0.15 * H <= y <= y_max - 0.20 * H:
        col_xs = np.where(crop_mask[y, :] > 127)[0]
        if len(col_xs) > 0:
            left_wall_pts.append((float(col_xs[0]), float(y)))
            right_wall_pts.append((float(col_xs[-1]), float(y)))

left_wall_pts = np.array(left_wall_pts)
right_wall_pts = np.array(right_wall_pts)

# Fit linear lateral lines: x = m*y + c
poly_L = np.polyfit(left_wall_pts[:, 1], left_wall_pts[:, 0], deg=1) # [m_L, c_L]
poly_R = np.polyfit(right_wall_pts[:, 1], right_wall_pts[:, 0], deg=1) # [m_R, c_R]

# 3. Step 2: Determine Bottle Axis as the Angle Bisector / Central Axis
# Slope angles: theta = arctan(m) in degrees (relative to vertical)
theta_L = np.degrees(np.arctan(poly_L[0]))
theta_R = np.degrees(np.arctan(poly_R[0]))
theta_axis = (theta_L + theta_R) / 2.0

print(f"Lateral Left Slope Angle: {theta_L:.2f} deg")
print(f"Lateral Right Slope Angle: {theta_R:.2f} deg")
print(f"Central Axis Tilt Angle: {theta_axis:.2f} deg")

# Central pivot point for rotation
center_x = (np.mean(left_wall_pts[:, 0]) + np.mean(right_wall_pts[:, 0])) / 2.0
center_y = (y_min + y_max) / 2.0
pivot = (float(center_x), float(center_y))

# 4. Step 3: Rotate Image and Mask so Axis is 100% Vertical!
rot_mat = cv2.getRotationMatrix2D(pivot, theta_axis, 1.0)
rot_img = cv2.warpAffine(crop_bgr, rot_mat, (cw, ch), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
rot_mask = cv2.warpAffine(crop_mask, rot_mat, (cw, ch), flags=cv2.INTER_NEAREST)

# Clean rotated mask
rot_binary = np.uint8(rot_mask > 127)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(rot_binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask = np.zeros_like(rot_mask)
    clean_mask[labels == largest_label] = 255
    rot_mask = clean_mask

# 5. Step 4: Now do everything else in Canonical Upright Space!
# In upright space, the axis is perfectly vertical (x = center_x)
y_indices_rot, x_indices_rot = np.where(rot_mask > 127)
y_min_r, y_max_r = int(np.min(y_indices_rot)), int(np.max(y_indices_rot))
x_min_r, x_max_r = int(np.min(x_indices_rot)), int(np.max(x_indices_rot))
H_r = y_max_r - y_min_r

# Exact Left & Right Silhouette Polylines
valid_ys_rot = np.unique(y_indices_rot)
left_wall_r = []
right_wall_r = []
for y in valid_ys_rot:
    col_xs = np.where(rot_mask[y, :] > 127)[0]
    if len(col_xs) > 0:
        left_wall_r.append((float(col_xs[0]), float(y)))
        right_wall_r.append((float(col_xs[-1]), float(y)))
left_wall_r = np.array(left_wall_r)
right_wall_r = np.array(right_wall_r)

# Corners:
left_top_idx = np.argmin((left_wall_r[:, 0] - x_min_r) + 1.2 * (left_wall_r[:, 1] - y_min_r))
P_TL_r = left_wall_r[left_top_idx]

left_bot_candidates = left_wall_r[left_wall_r[:, 1] >= y_min_r + 0.65 * H_r]
left_bot_idx = np.argmin(left_bot_candidates[:, 0] + 0.15 * (y_max_r - left_bot_candidates[:, 1]))
P_BL_r = left_bot_candidates[left_bot_idx]

right_top_idx = np.argmin((x_max_r - right_wall_r[:, 0]) + 1.2 * (right_wall_r[:, 1] - y_min_r))
P_TR_r = right_wall_r[right_top_idx]

right_bot_candidates = right_wall_r[right_wall_r[:, 1] >= y_min_r + 0.65 * H_r]
right_bot_idx = np.argmin((x_max_r - right_bot_candidates[:, 0]) + 0.15 * (y_max_r - right_bot_candidates[:, 1]))
P_BR_r = right_bot_candidates[right_bot_idx]

N_pts = 45
ys_left = np.linspace(P_TL_r[1], P_BL_r[1], N_pts)
L_pts_r = []
for y in ys_left:
    y_int = int(np.clip(round(y), 0, ch - 1))
    col_xs = np.where(rot_mask[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        L_pts_r.append((float(col_xs[0]), y))
    else:
        L_pts_r.append((P_TL_r[0], y))
L_curve_r = np.array(L_pts_r)
L_curve_r[:, 0] = cv2.GaussianBlur(L_curve_r[:, 0].reshape(-1, 1), (5, 1), 1.0).ravel()
L_curve_r[0], L_curve_r[-1] = P_TL_r, P_BL_r

ys_right = np.linspace(P_TR_r[1], P_BR_r[1], N_pts)
R_pts_r = []
for y in ys_right:
    y_int = int(np.clip(round(y), 0, ch - 1))
    col_xs = np.where(rot_mask[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        R_pts_r.append((float(col_xs[-1]), y))
    else:
        R_pts_r.append((P_TR_r[0], y))
R_curve_r = np.array(R_pts_r)
R_curve_r[:, 0] = cv2.GaussianBlur(R_curve_r[:, 0].reshape(-1, 1), (5, 1), 1.0).ravel()
R_curve_r[0], R_curve_r[-1] = P_TR_r, P_BR_r

# Canonical Symmetrical Bottom Semi-Ellipse (in upright space!):
xs_bot = np.linspace(P_BL_r[0], P_BR_r[0], N_pts)
raw_ys_bot = []
for x in xs_bot:
    x_int = int(np.clip(round(x), 0, cw - 1))
    col_ys = np.where(rot_mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_bot.append(float(np.max(col_ys)))
    else:
        raw_ys_bot.append(P_BL_r[1])
raw_ys_bot = np.array(raw_ys_bot)

mid_idx = len(raw_ys_bot) // 2
mid_span = max(1, int(len(raw_ys_bot) * 0.15))
y_apex_bot = float(np.median(raw_ys_bot[mid_idx - mid_span : mid_idx + mid_span]))

x0_bot = (P_BL_r[0] + P_BR_r[0]) / 2.0
a_bot = max((P_BR_r[0] - P_BL_r[0]) / 2.0, 1.0)
y_corner_avg_bot = (P_BL_r[1] + P_BR_r[1]) / 2.0
b_bot = max(y_apex_bot - y_corner_avg_bot, 4.0)

theta = np.linspace(0.0, np.pi, N_pts)
B_ell_x = x0_bot - a_bot * np.cos(theta)
B_ell_y = y_corner_avg_bot + b_bot * np.sin(theta) + (1.0 - theta / np.pi) * P_BL_r[1] + (theta / np.pi) * P_BR_r[1] - y_corner_avg_bot
B_ell_y[0], B_ell_y[-1] = P_BL_r[1], P_BR_r[1]
B_curve_r = np.column_stack((B_ell_x, B_ell_y))

# Canonical Symmetrical Top Semi-Ellipse:
xs_top = np.linspace(P_TL_r[0], P_TR_r[0], N_pts)
raw_ys_top = []
for x in xs_top:
    x_int = int(np.clip(round(x), 0, cw - 1))
    col_ys = np.where(rot_mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_top.append(float(np.min(col_ys)))
    else:
        raw_ys_top.append(P_TL_r[1])
raw_ys_top = np.array(raw_ys_top)

y_apex_top = float(np.median(raw_ys_top[mid_idx - mid_span : mid_idx + mid_span]))
x0_top = (P_TL_r[0] + P_TR_r[0]) / 2.0
a_top = max((P_TR_r[0] - P_TL_r[0]) / 2.0, 1.0)
y_corner_avg_top = (P_TL_r[1] + P_TR_r[1]) / 2.0
b_top = max(y_corner_avg_top - y_apex_top, 4.0)

T_ell_x = x0_top - a_top * np.cos(theta)
T_ell_y = y_corner_avg_top - b_top * np.sin(theta) + (1.0 - theta / np.pi) * P_TL_r[1] + (theta / np.pi) * P_TR_r[1] - y_corner_avg_top
T_ell_y[0] = P_TL_r[1]
T_ell_y[-1] = P_TR_r[1]
T_curve_r = np.column_stack((T_ell_x, T_ell_y))

# 6. Render Upright Axis & Mesh Visuals
vis_upright = rot_img.copy()
mask_2d_r = rot_mask > 127
green_layer_r = rot_img.copy()
green_layer_r[mask_2d_r] = [40, 225, 60]
vis_upright[mask_2d_r] = cv2.addWeighted(rot_img[mask_2d_r], 0.65, green_layer_r[mask_2d_r], 0.35, 0)

# Draw Central Vertical Axis (Red Line)
cv2.line(vis_upright, (int(center_x), 0), (int(center_x), ch - 1), (0, 0, 255), 2, cv2.LINE_AA)

# Blue lateral
cv2.polylines(vis_upright, [L_curve_r.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_upright, [R_curve_r.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Green Ellipsoids
cv2.polylines(vis_upright, [T_curve_r.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_upright, [B_curve_r.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL_r, P_TR_r, P_BL_r, P_BR_r]:
    cv2.circle(vis_upright, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_upright, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# Build Orthogonal Coon's Patch 3D Grid in Upright Space
u_vals = np.linspace(0.0, 1.0, 31)
v_vals = np.linspace(0.0, 1.0, 31)
idx_orig = np.linspace(0.0, 1.0, N_pts)

T_resamp = np.column_stack((np.interp(u_vals, idx_orig, T_curve_r[:, 0]), np.interp(u_vals, idx_orig, T_curve_r[:, 1])))
B_resamp = np.column_stack((np.interp(u_vals, idx_orig, B_curve_r[:, 0]), np.interp(u_vals, idx_orig, B_curve_r[:, 1])))
L_resamp = np.column_stack((np.interp(v_vals, idx_orig, L_curve_r[:, 0]), np.interp(v_vals, idx_orig, L_curve_r[:, 1])))
R_resamp = np.column_stack((np.interp(v_vals, idx_orig, R_curve_r[:, 0]), np.interp(v_vals, idx_orig, R_curve_r[:, 1])))

u_grid = np.zeros((31, 31), dtype=np.float32)
v_grid = np.zeros((31, 31), dtype=np.float32)
for i in range(31):
    v = v_vals[i]
    for j in range(31):
        u = u_vals[j]
        corner_blend = (1.0 - u) * (1.0 - v) * P_TL_r + u * (1.0 - v) * P_TR_r + (1.0 - u) * v * P_BL_r + u * v * P_BR_r
        pt = (1.0 - v) * T_resamp[j] + v * B_resamp[j] + (1.0 - u) * L_resamp[i] + u * R_resamp[i] - corner_blend
        u_grid[i, j] = pt[0]
        v_grid[i, j] = pt[1]

vis_mesh_upright = rot_img.copy()
cv2.line(vis_mesh_upright, (int(center_x), 0), (int(center_x), ch - 1), (0, 0, 255), 2, cv2.LINE_AA)
cv2.polylines(vis_mesh_upright, [L_curve_r.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_mesh_upright, [R_curve_r.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

for i in range(31):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 255, 0) if (i == 0 or i == 30) else (0, 240, 255)
    thick = 3 if (i == 0 or i == 30) else 1
    cv2.polylines(vis_mesh_upright, [pts], False, color, thick, cv2.LINE_AA)
for j in range(31):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    cv2.polylines(vis_mesh_upright, [pts], False, (0, 240, 255), 1, cv2.LINE_AA)
for pt in [P_TL_r, P_TR_r, P_BL_r, P_BR_r]:
    cv2.circle(vis_mesh_upright, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mesh_upright, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# Remap in Upright Space
dst_w = int(max(np.linalg.norm(P_TR_r - P_TL_r), np.linalg.norm(P_BR_r - P_BL_r)))
dst_h = int(max(np.linalg.norm(P_BL_r - P_TL_r), np.linalg.norm(P_BR_r - P_TR_r)))
map_x_flat = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
map_y_flat = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)

dewarped_upright = cv2.remap(rot_img, map_x_flat, map_y_flat, interpolation=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)

# OCR on Upright Dewarped
from pipeline.stage5_ocr import Stage5OCRDecoder
ocr_engine = Stage5OCRDecoder()
ocr_res = ocr_engine.process(dewarped_upright)

print("OCR on Upright Rectified Dewarped:")
for t in ocr_res.get("text_blocks", []):
    print(f"  - {t['text']} (conf: {t['confidence']*100:.1f}%)")

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "rectified_upright_overlay.png"), vis_upright)
cv2.imwrite(os.path.join(artifacts_dir, "rectified_upright_mesh.png"), vis_mesh_upright)
cv2.imwrite(os.path.join(artifacts_dir, "rectified_upright_dewarped.png"), dewarped_upright)
cv2.imwrite(os.path.join(artifacts_dir, "rectified_upright_annotated.png"), ocr_res.get("annotated_image"))

print("Saved all upright rectification artifacts successfully!")
