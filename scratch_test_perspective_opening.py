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

# 1. Measured top curve sagitta (from unobstructed top edge)
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

a_top = W_top / 2.0
opening_ratio_top = delta_top / a_top

print(f"Top Sagitta delta_top = {delta_top:.1f}px, a_top = {a_top:.1f}px -> Opening Ratio e_top = {opening_ratio_top:.3f}")

# 2. Projective Law of Ellipse Opening (Закон раскрытия эллипсов):
# e(y) = e_top + (y - y_top) * de/dy
# In perspective for photos at 0.5-0.8m distance (focal ~ 1.2 * image_width):
# de/dy = (1.0 / (Focal * cos^2(tilt))) ~ 0.08 - 0.10 / W_avg
rate_opening = 0.085 / W_avg
opening_ratio_bot = opening_ratio_top + H * rate_opening

a_bot = W_bot / 2.0
delta_bot_geom = opening_ratio_bot * a_bot

print(f"Geometric Bottom Opening Ratio e_bot = {opening_ratio_bot:.3f} -> Reconstructed Sagitta delta_bot = {delta_bot_geom:.1f}px")

# Reconstruct bottom semi-ellipse:
N_pts = 45
theta = np.linspace(0.0, np.pi, N_pts)
x0_bot = (P_BL[0] + P_BR[0]) / 2.0
B_geom_x = x0_bot - a_bot * np.cos(theta)
y_corners_bot = (P_BL[1] + P_BR[1]) / 2.0
tilt_bot = (1.0 - theta / np.pi) * P_BL[1] + (theta / np.pi) * P_BR[1] - y_corners_bot
B_geom_y = y_corners_bot + delta_bot_geom * np.sin(theta) + tilt_bot
B_geom_y[0], B_geom_y[-1] = P_BL[1], P_BR[1]
B_geom_curve = np.column_stack((B_geom_x, B_geom_y))

# Build Coon's Patch grid with Geometric Opening
T_curve = vm.T_curve
L_curve = vm.L_line
R_curve = vm.R_line

u_vals = np.linspace(0.0, 1.0, 31)
v_vals = np.linspace(0.0, 1.0, 31)
idx_T = np.linspace(0.0, 1.0, len(T_curve))
idx_B = np.linspace(0.0, 1.0, len(B_geom_curve))
idx_L = np.linspace(0.0, 1.0, len(L_curve))
idx_R = np.linspace(0.0, 1.0, len(R_curve))

T_resamp = np.column_stack((np.interp(u_vals, idx_T, T_curve[:, 0]), np.interp(u_vals, idx_T, T_curve[:, 1])))
B_resamp = np.column_stack((np.interp(u_vals, idx_B, B_geom_curve[:, 0]), np.interp(u_vals, idx_B, B_geom_curve[:, 1])))
L_resamp = np.column_stack((np.interp(v_vals, idx_L, L_curve[:, 0]), np.interp(v_vals, idx_L, L_curve[:, 1])))
R_resamp = np.column_stack((np.interp(v_vals, idx_R, R_curve[:, 0]), np.interp(v_vals, idx_R, R_curve[:, 1])))

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

# Render Visual
vis = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Blue lateral
cv2.polylines(vis, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Top Ellipse & Perspective Opened Bottom Ellipse
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [B_geom_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# Draw Mesh
vis_mesh = crop_bgr.copy()
cv2.polylines(vis_mesh, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_mesh, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
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

print("OCR on Geometric Opening Dewarped:")
for t in ocr_res.get("text_blocks", []):
    print(f"  - {t['text']} (conf: {t['confidence']*100:.1f}%)")

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "belbek_perspective_opening_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "belbek_perspective_opening_mesh.png"), vis_mesh)
cv2.imwrite(os.path.join(artifacts_dir, "belbek_perspective_opening_dewarped.png"), enhanced)
cv2.imwrite(os.path.join(artifacts_dir, "belbek_perspective_opening_annotated.png"), ocr_res.get("annotated_bgr"))

print("Saved all Belbek perspective opening artifacts successfully!")
