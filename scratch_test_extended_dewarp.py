import cv2
import numpy as np
import os
import json
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage4_remapping import Stage4Remapper
from rapidocr_onnxruntime import RapidOCR

# 1. Load Terra Argenta Image and Mask Components
img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-30 (3).jpg"
img_bgr = cv2.imread(img_path)
h_full, w_full = img_bgr.shape[:2]

mask_lower = cv2.imread("scratch_debug/terra_mask_lower.png", cv2.IMREAD_GRAYSCALE)
mask_upper = cv2.imread("scratch_debug/terra_mask_upper.png", cv2.IMREAD_GRAYSCALE)

# Vectorize lower rectangular label
vec = MaskVectorizer()
vm = vec.vectorize(mask_lower)

P_TL = vm.P_TL
P_TR = vm.P_TR
P_BL = vm.P_BL
P_BR = vm.P_BR

# 2. Compute Upward Extension based on Upper Label Apex
y_up_indices, x_up_indices = np.where(mask_upper > 127)
y_top_apex = float(np.min(y_up_indices)) if len(y_up_indices) > 0 else 0.0

H_lower = (P_BL[1] + P_BR[1]) / 2.0 - (P_TL[1] + P_TR[1]) / 2.0
y_lower_top = (P_TL[1] + P_TR[1]) / 2.0
y_extend_top = max(0.0, y_top_apex - 25.0)

ext_h = max(0.0, y_lower_top - y_extend_top)
v_ext_ratio = ext_h / max(H_lower, 1.0)

print(f"Lower label height: {H_lower:.1f}px, extend upward by: {ext_h:.1f}px (ratio: {v_ext_ratio:.2f})")

# Extrapolate lateral generators upwards along cylinder axis
P_TL_ext = P_TL - v_ext_ratio * (P_BL - P_TL)
P_TR_ext = P_TR - v_ext_ratio * (P_BR - P_TR)

# 3. Construct Unified 3D Coon's Patch Grid covering BOTH labels
N_rows = 40
N_cols = 30

u_vals = np.linspace(0.0, 1.0, N_cols)
v_vals = np.linspace(0.0, 1.0, N_rows)

curve_dy = vm.T_curve[:, 1] - np.linspace(P_TL[1], P_TR[1], len(vm.T_curve))

T_ext_x = np.linspace(P_TL_ext[0], P_TR_ext[0], N_cols)
T_ext_y = np.linspace(P_TL_ext[1], P_TR_ext[1], N_cols) + np.interp(u_vals, np.linspace(0, 1, len(curve_dy)), curve_dy) * 0.8

B_ext_x = np.linspace(P_BL[0], P_BR[0], N_cols)
B_ext_y = np.linspace(P_BL[1], P_BR[1], N_cols) + np.interp(u_vals, np.linspace(0, 1, len(curve_dy)), curve_dy) * 1.0

u_grid = np.zeros((N_rows, N_cols), dtype=np.float32)
v_grid = np.zeros((N_rows, N_cols), dtype=np.float32)

L_ext = (1.0 - v_vals[:, None]) * P_TL_ext + v_vals[:, None] * P_BL
R_ext = (1.0 - v_vals[:, None]) * P_TR_ext + v_vals[:, None] * P_BR

for i in range(N_rows):
    v = v_vals[i]
    for j in range(N_cols):
        u = u_vals[j]
        corner_blend = (1.0 - u) * (1.0 - v) * P_TL_ext + u * (1.0 - v) * P_TR_ext + (1.0 - u) * v * P_BL + u * v * P_BR
        pt_T = np.array([T_ext_x[j], T_ext_y[j]])
        pt_B = np.array([B_ext_x[j], B_ext_y[j]])
        pt = (1.0 - v) * pt_T + v * pt_B + (1.0 - u) * L_ext[i] + u * R_ext[i] - corner_blend
        u_grid[i, j] = pt[0]
        v_grid[i, j] = pt[1]

# 4. Dense Backward Remapping via Stage4Remapper
out_w = 600
out_h = int(out_w * (H_lower + ext_h) / max(float(np.linalg.norm(P_TR - P_TL)), 1.0))

src_ctrl_pts = np.column_stack((u_grid.flatten(), v_grid.flatten())).astype(np.float32)
u_dst, v_dst = np.meshgrid(np.linspace(0, out_w - 1, N_cols), np.linspace(0, out_h - 1, N_rows))
dst_ctrl_pts = np.column_stack((u_dst.flatten(), v_dst.flatten())).astype(np.float32)

remapper = Stage4Remapper()
map_x, map_y = remapper.compute_dense_backward_map(src_ctrl_pts, dst_ctrl_pts, (out_h, out_w))
dewarped_full = remapper.remap_lanczos(img_bgr, map_x, map_y)
dewarped_full = remapper.postprocess_orthographic_scan(dewarped_full)

# 5. Visual 3D Mesh on Bottle Image
vis_mesh = img_bgr.copy()
for i in range(N_rows):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 255, 0) if (i == 0 or i == N_rows - 1) else (0, 240, 255)
    thick = 3 if (i == 0 or i == N_rows - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, cv2.LINE_AA)

for j in range(N_cols):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    color = (255, 140, 0) if (j == 0 or j == N_cols - 1) else (0, 180, 255)
    thick = 3 if (j == 0 or j == N_cols - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, cv2.LINE_AA)

# Draw 4 extended corners
for pt in [P_TL_ext, P_TR_ext, P_BL, P_BR]:
    cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# 6. High-Precision OCR on Full Unified Scan
rapid = RapidOCR()
ocr_res, _ = rapid(dewarped_full)

vis_ocr = dewarped_full.copy()
print("\n" + "="*60)
print("   RECOGNIZED TEXT ON FULL UNIFIED EXTENDED SCAN")
print("="*60)
if ocr_res:
    for idx, (bbox, text, conf) in enumerate(ocr_res, 1):
        print(f"[{idx:02d}] {text:<35} | Точность: {conf*100:.1f}%")
        pts = np.array(bbox, dtype=np.int32)
        cv2.polylines(vis_ocr, [pts], True, (0, 255, 0), 2, cv2.LINE_AA)
        label_str = f"{text} ({conf*100:.0f}%)"
        (t_w, t_h), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y = max(pts[0][1] - 4, t_h + 4)
        cv2.rectangle(vis_ocr, (pts[0][0], tag_y - t_h - 2), (pts[0][0] + t_w + 6, tag_y + 2), (0, 0, 0), -1)
        cv2.putText(vis_ocr, label_str, (pts[0][0] + 3, tag_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
print("="*60)

# Save artifacts
artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "terra_extended_mesh.png"), vis_mesh)
cv2.imwrite(os.path.join(artifacts_dir, "terra_extended_dewarped.png"), dewarped_full)
cv2.imwrite(os.path.join(artifacts_dir, "terra_extended_ocr.png"), vis_ocr)

print("Saved all extended cylinder dewarp artifacts successfully!")
