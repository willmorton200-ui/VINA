import cv2
import numpy as np
import os

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

# 1. Morphological closing
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask_closed = cv2.morphologyEx(crop_mask, cv2.MORPH_CLOSE, kernel)

# 2. Extract row-by-row left and right points along the mask
y_indices, x_indices = np.where(mask_closed > 127)
valid_ys = np.unique(y_indices)
left_pts = []
right_pts = []
for y in valid_ys:
    col_xs = np.where(mask_closed[y, :] > 127)[0]
    if len(col_xs) > 0:
        left_pts.append((float(col_xs[0]), float(y)))
        right_pts.append((float(col_xs[-1]), float(y)))

left_pts = np.array(left_pts)   # (x, y)
right_pts = np.array(right_pts) # (x, y)

# 3. Fit Lateral Tangents (Линейная регрессия по средним 60% высоты)
y_min = int(np.min(valid_ys))
y_max = int(np.max(valid_ys))
H_mask = y_max - y_min

L_mid = left_pts[(left_pts[:, 1] >= y_min + 0.20 * H_mask) & (left_pts[:, 1] <= y_min + 0.80 * H_mask)]
R_mid = right_pts[(right_pts[:, 1] >= y_min + 0.20 * H_mask) & (right_pts[:, 1] <= y_min + 0.80 * H_mask)]

poly_L = np.polyfit(L_mid[:, 1], L_mid[:, 0], deg=1) # x = m_L * y + c_L
poly_R = np.polyfit(R_mid[:, 1], R_mid[:, 0], deg=1) # x = m_R * y + c_R

print("=== БОКОВЫЕ КАСАТЕЛЬНЫЕ ===")
print(f"  Левая касательная:  x = {poly_L[0]:.4f} * y + {poly_L[1]:.1f}")
print(f"  Правая касательная: x = {poly_R[0]:.4f} * y + {poly_R[1]:.1f}")

# 4. Physical Boundary Levels of Horizontal Guides from Mask:
# Top guide height level
top_ys = [pt[1] for pt in left_pts if pt[1] <= y_min + 0.15 * H_mask]
y_top_ref = float(np.median(top_ys)) if len(top_ys) > 0 else float(y_min)

# Bottom guide:
# Left flank ends at inflection point around y ~ 488
y_bl_ref = 488.0
# Right flank ends at inflection point around y ~ 540
y_br_ref = 540.0
# Absolute apex of bottom arc
y_bot_apex = float(y_max) # 618.0

# 5. Compute Exact Intersection Points (Угловые вершины):
P_TL = np.array([poly_L[0] * y_top_ref + poly_L[1], y_top_ref])
P_TR = np.array([poly_R[0] * (y_top_ref + 15.0) + poly_R[1], y_top_ref + 15.0])
P_BL = np.array([poly_L[0] * y_bl_ref + poly_L[1], y_bl_ref])
P_BR = np.array([poly_R[0] * y_br_ref + poly_R[1], y_br_ref])

print("\n=== ТОЧКИ ПЕРЕСЕЧЕНИЯ (УГЛОВЫЕ ТОЧКИ) ===")
print(f"  P_TL = [{P_TL[0]:.1f}, {P_TL[1]:.1f}]")
print(f"  P_TR = [{P_TR[0]:.1f}, {P_TR[1]:.1f}]")
print(f"  P_BL = [{P_BL[0]:.1f}, {P_BL[1]:.1f}]")
print(f"  P_BR = [{P_BR[0]:.1f}, {P_BR[1]:.1f}]")

# 6. Construct Continuous Horizontal Guide Semi-Ellipses between Intersections:
N_pts = 60
theta = np.linspace(0.0, np.pi, N_pts)

# Top Semi-Ellipse T(u):
a_top = (P_TR[0] - P_TL[0]) / 2.0
x0_top = (P_TL[0] + P_TR[0]) / 2.0
y_corners_top = (P_TL[1] + P_TR[1]) / 2.0
delta_top = 10.0 # gentle top smile
tilt_top = (1.0 - theta / np.pi) * P_TL[1] + (theta / np.pi) * P_TR[1] - y_corners_top

T_ell_x = x0_top - a_top * np.cos(theta)
T_ell_y = y_corners_top + delta_top * np.sin(theta) + tilt_top
T_ell_y[0], T_ell_y[-1] = P_TL[1], P_TR[1]
T_curve = np.column_stack((T_ell_x, T_ell_y))

# Bottom Semi-Ellipse B(u) (SMILE through y_bot_apex = 618):
a_bot = (P_BR[0] - P_BL[0]) / 2.0
x0_bot = (P_BL[0] + P_BR[0]) / 2.0
y_corners_bot = (P_BL[1] + P_BR[1]) / 2.0
delta_bot = y_bot_apex - y_corners_bot # 618 - 514 = +104 px
tilt_bot = (1.0 - theta / np.pi) * P_BL[1] + (theta / np.pi) * P_BR[1] - y_corners_bot

B_ell_x = x0_bot - a_bot * np.cos(theta)
B_ell_y = y_corners_bot + delta_bot * np.sin(theta) + tilt_bot
B_ell_y[0], B_ell_y[-1] = P_BL[1], P_BR[1]
B_curve = np.column_stack((B_ell_x, B_ell_y))

# Lateral Tangent Segments L(v) and R(v):
v_vals = np.linspace(0.0, 1.0, N_pts)
L_curve = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
R_curve = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR

print(f"\nНижняя направляющая (SMILE):")
print(f"  y_corners_avg = {y_corners_bot:.1f}px, y_apex = {y_bot_apex:.1f}px -> delta_bot = +{delta_bot:.1f}px")

# 7. Render Visualization Overlay
vis = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Full Yellow Tangent Lines
y_full = np.linspace(0, h - 1, 100)
x_L_full = poly_L[0] * y_full + poly_L[1]
x_R_full = poly_R[0] * y_full + poly_R[1]
pts_L_full = np.column_stack((x_L_full, y_full)).astype(np.int32)
pts_R_full = np.column_stack((x_R_full, y_full)).astype(np.int32)
cv2.polylines(vis, [pts_L_full], False, (0, 255, 255), 2, cv2.LINE_AA)
cv2.polylines(vis, [pts_R_full], False, (0, 255, 255), 2, cv2.LINE_AA)

# Bounded Lateral Edges along tangents (Orange)
cv2.polylines(vis, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Horizontal Guide Curves from Mask (Green)
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

# Corner Intersections (White/Green Circles)
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 10, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# 8. Build 3D Mesh
u_vals = np.linspace(0.0, 1.0, 31)
v_vals = np.linspace(0.0, 1.0, 31)
idx_pts = np.linspace(0.0, 1.0, N_pts)

T_resamp = np.column_stack((np.interp(u_vals, idx_pts, T_curve[:, 0]), np.interp(u_vals, idx_pts, T_curve[:, 1])))
B_resamp = np.column_stack((np.interp(u_vals, idx_pts, B_curve[:, 0]), np.interp(u_vals, idx_pts, B_curve[:, 1])))
L_resamp = np.column_stack((np.interp(v_vals, idx_pts, L_curve[:, 0]), np.interp(v_vals, idx_pts, L_curve[:, 1])))
R_resamp = np.column_stack((np.interp(v_vals, idx_pts, R_curve[:, 0]), np.interp(v_vals, idx_pts, R_curve[:, 1])))

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

# 9. Remap & OCR
W_avg = (np.linalg.norm(P_TR - P_TL) + np.linalg.norm(P_BR - P_BL)) / 2.0
H_avg = (np.linalg.norm(P_BL - P_TL) + np.linalg.norm(P_BR - P_TR)) / 2.0
dst_w = int(W_avg)
dst_h = int(H_avg)

from pipeline.stage4_remapping import Stage4Remapper
remapper = Stage4Remapper()
dewarped = remapper.remap_gpu(crop_bgr, u_grid, v_grid, (dst_h, dst_w))
enhanced = remapper.postprocess_orthographic_scan(dewarped)

from pipeline.stage5_ocr import Stage5OCRDecoder
ocr = Stage5OCRDecoder()
ocr_res = ocr.process(enhanced)

print(f"\nOCR Detected {len(ocr_res.get('text_blocks', []))} text tokens:")
for t in ocr_res.get("text_blocks", []):
    print(f"  - {t['text']} ({t['confidence']*100:.1f}%)")

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "castillo_guides_tangents_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_guides_tangents_mesh.png"), vis_mesh)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_guides_tangents_dewarped.png"), enhanced)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_guides_tangents_annotated.png"), ocr_res.get("annotated_bgr"))

print("\nSaved all Castillo guides + tangents artifacts successfully!")
