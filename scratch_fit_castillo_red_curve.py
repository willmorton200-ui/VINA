import cv2
import numpy as np
import os
import matplotlib.pyplot as plt

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

# 1. Morphological closing
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask_closed = cv2.morphologyEx(crop_mask, cv2.MORPH_CLOSE, kernel)

# 2. Extract contour of the mask
contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea).squeeze() # (N, 2) [x, y]

# 3. Exact Corner Identification:
# Find P_TL: point with minimum (x + 1.2*y)
score_TL = cnt[:, 0] + 1.2 * cnt[:, 1]
P_TL = cnt[np.argmin(score_TL)].astype(np.float64)

# Find P_TR: point with minimum (-x + 1.2*y)
score_TR = -cnt[:, 0] + 1.2 * cnt[:, 1]
P_TR = cnt[np.argmin(score_TR)].astype(np.float64)

# Find P_BL: leftmost point among the lower half of the mask
# (where the left vertical flank ends and transitions into the bottom arc!)
lower_left = cnt[(cnt[:, 1] > h * 0.40) & (cnt[:, 0] < w * 0.45)]
# On the left flank, x is small. As we go down the left flank, x is near the minimum.
# The bottom-left corner is the point with minimum x (or min x + 0.3*y) in this lower-left region:
score_BL = lower_left[:, 0] - 0.2 * lower_left[:, 1]
P_BL = lower_left[np.argmin(score_BL)].astype(np.float64)

# Find P_BR: rightmost point among the lower half of the mask
# (where the right vertical flank ends and transitions into the bottom arc!)
lower_right = cnt[(cnt[:, 1] > h * 0.40) & (cnt[:, 0] > w * 0.55)]
score_BR = -lower_right[:, 0] - 0.2 * lower_right[:, 1]
P_BR = lower_right[np.argmin(score_BR)].astype(np.float64)

print("=== EXACT CORNERS ===")
print(f"  P_TL = [{P_TL[0]:.1f}, {P_TL[1]:.1f}]")
print(f"  P_TR = [{P_TR[0]:.1f}, {P_TR[1]:.1f}]")
print(f"  P_BL = [{P_BL[0]:.1f}, {P_BL[1]:.1f}] (where bottom arc starts on left)")
print(f"  P_BR = [{P_BR[0]:.1f}, {P_BR[1]:.1f}] (where bottom arc ends on right)")

# 4. Extract Bottom Contour between P_BL and P_BR:
N_pts = 60
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

# Apex (lowest point) of the bottom arc along the red curve
mid_idx = len(raw_ys_bot) // 2
mid_span = max(1, int(len(raw_ys_bot) * 0.15))
y_apex_bot = float(np.median(raw_ys_bot[mid_idx - mid_span : mid_idx + mid_span]))

y_corners_bot = (P_BL[1] + P_BR[1]) / 2.0
delta_bot = y_apex_bot - y_corners_bot # sagitta pro-gib downwards!

x0_bot = (P_BL[0] + P_BR[0]) / 2.0
a_bot = max((P_BR[0] - P_BL[0]) / 2.0, 1.0)

print(f"\nBottom Semi-Ellipse (SMILE):")
print(f"  x0 = {x0_bot:.1f}, a = {a_bot:.1f}px")
print(f"  y_corners_avg = {y_corners_bot:.1f}px, y_apex = {y_apex_bot:.1f}px")
print(f"  delta_bot = +{delta_bot:.1f}px (DEEP SMILE PRO-GIB DOWNWARDS!)")

# 5. Extract Top Contour between P_TL and P_TR:
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
y_corners_top = (P_TL[1] + P_TR[1]) / 2.0
delta_top = y_apex_top - y_corners_top

x0_top = (P_TL[0] + P_TR[0]) / 2.0
a_top = max((P_TR[0] - P_TL[0]) / 2.0, 1.0)

print(f"\nTop Semi-Ellipse:")
print(f"  x0 = {x0_top:.1f}, a = {a_top:.1f}px")
print(f"  y_corners_avg = {y_corners_top:.1f}px, y_apex = {y_apex_top:.1f}px")
print(f"  delta_top = {delta_top:.1f}px")

# 6. Fit Pure Semi-Ellipses (SMILE):
theta = np.linspace(0.0, np.pi, N_pts)

# Bottom Semi-Ellipse (SMILE)
B_ell_x = x0_bot - a_bot * np.cos(theta)
tilt_bot = (1.0 - theta / np.pi) * P_BL[1] + (theta / np.pi) * P_BR[1] - y_corners_bot
B_ell_y = y_corners_bot + delta_bot * np.sin(theta) + tilt_bot
B_ell_y[0], B_ell_y[-1] = P_BL[1], P_BR[1]
B_curve = np.column_stack((B_ell_x, B_ell_y))

# Top Semi-Ellipse
T_ell_x = x0_top - a_top * np.cos(theta)
tilt_top = (1.0 - theta / np.pi) * P_TL[1] + (theta / np.pi) * P_TR[1] - y_corners_top
T_ell_y = y_corners_top + delta_top * np.sin(theta) + tilt_top
T_ell_y[0], T_ell_y[-1] = P_TL[1], P_TR[1]
T_curve = np.column_stack((T_ell_x, T_ell_y))

# Left and Right Boundaries (strictly along the lateral flanks)
ys_L = np.linspace(P_TL[1], P_BL[1], N_pts)
L_curve = []
for y in ys_L:
    y_int = int(np.clip(round(y), 0, h - 1))
    col_xs = np.where(mask_closed[y_int, :] > 127)[0]
    L_curve.append((float(col_xs[0]) if len(col_xs) > 0 else P_TL[0], y))
L_curve = np.array(L_curve)
L_curve[:, 0] = cv2.GaussianBlur(L_curve[:, 0].reshape(-1, 1), (5, 1), 1.0).ravel()
L_curve[0], L_curve[-1] = P_TL, P_BL

ys_R = np.linspace(P_TR[1], P_BR[1], N_pts)
R_curve = []
for y in ys_R:
    y_int = int(np.clip(round(y), 0, h - 1))
    col_xs = np.where(mask_closed[y_int, :] > 127)[0]
    R_curve.append((float(col_xs[-1]) if len(col_xs) > 0 else P_TR[0], y))
R_curve = np.array(R_curve)
R_curve[:, 0] = cv2.GaussianBlur(R_curve[:, 0].reshape(-1, 1), (5, 1), 1.0).ravel()
R_curve[0], R_curve[-1] = P_TR, P_BR

# 7. Render Visualization Overlay
vis = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Lateral polylines (Blue / Orange)
cv2.polylines(vis, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Top & Bottom Semi-Ellipses (Green)
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

# Corner Points
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
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
cv2.imwrite(os.path.join(artifacts_dir, "castillo_true_red_curve_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_true_red_curve_mesh.png"), vis_mesh)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_true_red_curve_dewarped.png"), enhanced)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_true_red_curve_annotated.png"), ocr_res.get("annotated_bgr"))

print("Saved all Castillo true red curve artifacts successfully!")
