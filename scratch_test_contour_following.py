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

# Morphological closing to fill tiny single-pixel boundary notches while preserving full shape
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

y_indices, x_indices = np.where(mask_closed > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))

# 2. Extract Exact Boundary Contours
# Top profile: min y for each x
# Bottom profile: max y for each x
# Left profile: min x for each y
# Right profile: max x for each y

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

# 3. Corners on exact mask perimeter
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

print(f"Physical Corners on Perimeter:")
print(f"  P_TL: {P_TL}")
print(f"  P_TR: {P_TR}")
print(f"  P_BL: {P_BL}")
print(f"  P_BR: {P_BR}")

# 4. Direct Contour-Following Curves:
# Top curve T(u): Traces the exact upper contour between P_TL and P_TR
N_pts = 50
xs_top = np.linspace(P_TL[0], P_TR[0], N_pts)
T_pts = []
for x in xs_top:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask_closed[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        T_pts.append((x, float(np.min(col_ys))))
    else:
        T_pts.append((x, P_TL[1]))
T_curve = np.array(T_pts)
# Gentle Gaussian smoothing to remove 1px pixelation steps
T_curve[:, 1] = cv2.GaussianBlur(T_curve[:, 1].reshape(-1, 1), (5, 1), 1.2).ravel()
T_curve[0] = P_TL
T_curve[-1] = P_TR

# Bottom curve B(u): Traces the EXACT bottom contour between P_BL and P_BR
# (Hugs the outer edge around all text and golden borders)
xs_bot = np.linspace(P_BL[0], P_BR[0], N_pts)
B_pts = []
for x in xs_bot:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask_closed[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        B_pts.append((x, float(np.max(col_ys))))
    else:
        B_pts.append((x, P_BL[1]))
B_curve = np.array(B_pts)

# Filter any isolated spikes that jump > 12px from local median
med_filter_y = cv2.medianBlur(B_curve[:, 1].astype(np.float32), 5).ravel()
for i in range(len(B_curve)):
    if abs(B_curve[i, 1] - med_filter_y[i]) > 12:
        B_curve[i, 1] = med_filter_y[i]

# Gentle Gaussian smoothing of contour polyline
B_curve[:, 1] = cv2.GaussianBlur(B_curve[:, 1].reshape(-1, 1), (5, 1), 1.2).ravel()
B_curve[0] = P_BL
B_curve[-1] = P_BR

# Left lateral polyline L(v):
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
L_curve[:, 0] = cv2.GaussianBlur(L_curve[:, 0].reshape(-1, 1), (5, 1), 1.2).ravel()
L_curve[0] = P_TL
L_curve[-1] = P_BL

# Right lateral polyline R(v):
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
R_curve[:, 0] = cv2.GaussianBlur(R_curve[:, 0].reshape(-1, 1), (5, 1), 1.2).ravel()
R_curve[0] = P_TR
R_curve[-1] = P_BR

# 5. Render Comparison
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)

# Blue lateral polylines
cv2.polylines(vis_overlay, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Green curves along EXACT MASK BOUNDARY
cv2.polylines(vis_overlay, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

h_vis, w_vis = vis_overlay.shape[:2]
zoom_bl = vis_overlay[int(h_vis*0.4):, :int(w_vis*0.6)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_contour_following_overlay.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_contour_following.png"), zoom_bl)

print("Saved barakiani_contour_following_overlay.png and zoom successfully!")
