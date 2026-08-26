import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor

img_path = r"test_dataset/butilki/photo_2026-08-11_21-10-10.jpg"
img_bgr = cv2.imread(img_path)
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

from pipeline.vectorizer import MaskVectorizer
vec = MaskVectorizer()
vm = vec.vectorize(crop_mask)

P_TL = vm.P_TL
P_TR = vm.P_TR
P_BL = vm.P_BL
P_BR = vm.P_BR

W_top = np.linalg.norm(P_TR - P_TL)
W_bot = np.linalg.norm(P_BR - P_BL)
W_avg = (W_top + W_bot) / 2.0
H = ((P_BL[1] + P_BR[1]) - (P_TL[1] + P_TR[1])) / 2.0

a_top = W_top / 2.0
a_bot = W_bot / 2.0
aspect_ratio_hw = H / max(W_avg, 1.0)

# Top Sagitta
xs_top = np.linspace(P_TL[0], P_TR[0], len(vm.T_curve))
raw_ys_top = []
for x in xs_top:
    col_ys = np.where(crop_mask[:, int(np.clip(round(x), 0, w - 1))] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_top.append(float(np.min(col_ys)))
    else:
        raw_ys_top.append(P_TL[1])
raw_ys_top = np.array(raw_ys_top)

mid_idx = len(raw_ys_top) // 2
mid_span = max(1, int(len(raw_ys_top) * 0.15))
y_mid_top = float(np.median(raw_ys_top[mid_idx - mid_span : mid_idx + mid_span]))
y_corners_top = (P_TL[1] + P_TR[1]) / 2.0
delta_top = y_mid_top - y_corners_top
e_top = delta_top / a_top

# 3X Opening Gradient: kappa = 0.255 (~3x of 0.085)
e_bot_3x = e_top + aspect_ratio_hw * 0.255
delta_bot_3x = e_bot_3x * a_bot

print(f"Top: e_top = {e_top:.3f}, delta_top = {delta_top:.1f}px")
print(f"Bottom 3X Opening: e_bot = {e_bot_3x:.3f}, delta_bot = {delta_bot_3x:.1f}px")

# Construct Curves
N_pts = 45
theta = np.linspace(0.0, np.pi, N_pts)

# Top Ellipse
x0_top = (P_TL[0] + P_TR[0]) / 2.0
T_ell_x = x0_top - a_top * np.cos(theta)
tilt_top = (1.0 - theta / np.pi) * P_TL[1] + (theta / np.pi) * P_TR[1] - y_corners_top
T_ell_y = y_corners_top + delta_top * np.sin(theta) + tilt_top
T_ell_y[0], T_ell_y[-1] = P_TL[1], P_TR[1]
T_curve_3x = np.column_stack((T_ell_x, T_ell_y))

# Bottom Ellipse with 3x opening
x0_bot = (P_BL[0] + P_BR[0]) / 2.0
B_ell_x = x0_bot - a_bot * np.cos(theta)
y_corners_bot = (P_BL[1] + P_BR[1]) / 2.0
tilt_bot = (1.0 - theta / np.pi) * P_BL[1] + (theta / np.pi) * P_BR[1] - y_corners_bot
B_ell_y = y_corners_bot + delta_bot_3x * np.sin(theta) + tilt_bot
B_ell_y[0], B_ell_y[-1] = P_BL[1], P_BR[1]
B_curve_3x = np.column_stack((B_ell_x, B_ell_y))

# Coon's Patch Grid
u_vals = np.linspace(0.0, 1.0, 31)
v_vals = np.linspace(0.0, 1.0, 31)
idx_pts = np.linspace(0.0, 1.0, N_pts)

T_resamp = np.column_stack((np.interp(u_vals, idx_pts, T_curve_3x[:, 0]), np.interp(u_vals, idx_pts, T_curve_3x[:, 1])))
B_resamp = np.column_stack((np.interp(u_vals, idx_pts, B_curve_3x[:, 0]), np.interp(u_vals, idx_pts, B_curve_3x[:, 1])))
L_resamp = np.column_stack((np.interp(v_vals, idx_pts, vm.L_line[:, 0]), np.interp(v_vals, idx_pts, vm.L_line[:, 1])))
R_resamp = np.column_stack((np.interp(v_vals, idx_pts, vm.R_line[:, 0]), np.interp(v_vals, idx_pts, vm.R_line[:, 1])))

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

# Render Visuals
vis = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

cv2.polylines(vis, [vm.L_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vm.R_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [T_curve_3x.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [B_curve_3x.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

vis_mesh = crop_bgr.copy()
cv2.polylines(vis_mesh, [vm.L_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_mesh, [vm.R_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
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

# Remap
dst_w = int(W_avg)
dst_h = int(H)
from pipeline.stage4_remapping import Stage4Remapper
remapper = Stage4Remapper()
dewarped = remapper.remap_gpu(crop_bgr, u_grid, v_grid, (dst_h, dst_w))
enhanced = remapper.postprocess_orthographic_scan(dewarped)

from pipeline.stage5_ocr import Stage5OCRDecoder
ocr = Stage5OCRDecoder()
ocr_res = ocr.process(enhanced)

print("OCR on 3X Opening Dewarped:")
for t in ocr_res.get("text_blocks", []):
    print(f"  - {t['text']} (conf: {t['confidence']*100:.1f}%)")

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "belbek_3x_opening_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "belbek_3x_opening_mesh.png"), vis_mesh)
cv2.imwrite(os.path.join(artifacts_dir, "belbek_3x_opening_dewarped.png"), enhanced)
cv2.imwrite(os.path.join(artifacts_dir, "belbek_3x_opening_annotated.png"), ocr_res.get("annotated_bgr"))

print("Saved all Belbek 3X opening artifacts successfully!")
