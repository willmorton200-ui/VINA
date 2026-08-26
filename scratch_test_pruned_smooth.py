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

y_indices, x_indices = np.where(mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))

# 2. Extract Row-by-Row Left and Right Contour Points
valid_ys = np.unique(y_indices)
left_wall = []
right_wall = []
for y in valid_ys:
    col_xs = np.where(mask[y, :] > 127)[0]
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

print(f"Physical Corners: P_TL={P_TL}, P_TR={P_TR}, P_BL={P_BL}, P_BR={P_BR}")

# 4. Extract dense bottom profile
N_pts = 60
xs_bot = np.linspace(P_BL[0], P_BR[0], N_pts)
raw_ys_bot = []

for x in xs_bot:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_bot.append(float(np.max(col_ys)))
    else:
        raw_ys_bot.append(P_BL[1])

raw_ys_bot = np.array(raw_ys_bot)

# 5. Asymmetric Outlier Pruning (Prunes downward teeth while hugging the smooth label contour)
# Initial smooth polynomial fit
poly_trend = np.polyfit(xs_bot, raw_ys_bot, deg=2)
fitted_trend = np.polyval(poly_trend, xs_bot)

# Downward teeth have y > fitted_trend + threshold. We clamp them to the smooth envelope!
pruned_ys_bot = raw_ys_bot.copy()
for _ in range(5):
    fitted_trend = np.polyval(poly_trend, xs_bot)
    diff = pruned_ys_bot - fitted_trend
    # Points sticking DOWN (diff > 2.0) are teeth -> replace with fitted trend
    teeth_mask = diff > 2.0
    pruned_ys_bot[teeth_mask] = fitted_trend[teeth_mask]
    poly_trend = np.polyfit(xs_bot, pruned_ys_bot, deg=2)

# Now B_curve is the smooth contour that follows the label base, perfectly pruning all teeth!
B_y = np.polyval(poly_trend, xs_bot)
B_y[0] = P_BL[1]
B_y[-1] = P_BR[1]
B_curve = np.column_stack((xs_bot, B_y))

# 6. Extract Top curve with asymmetric upward pruning
xs_top = np.linspace(P_TL[0], P_TR[0], N_pts)
raw_ys_top = []
for x in xs_top:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_top.append(float(np.min(col_ys)))
    else:
        raw_ys_top.append(P_TL[1])
raw_ys_top = np.array(raw_ys_top)

poly_top_trend = np.polyfit(xs_top, raw_ys_top, deg=2)
pruned_ys_top = raw_ys_top.copy()
for _ in range(5):
    fitted_top = np.polyval(poly_top_trend, xs_top)
    diff = fitted_top - pruned_ys_top # Upward nipples have raw < fitted
    nipple_mask = diff > 2.0
    pruned_ys_top[nipple_mask] = fitted_top[nipple_mask]
    poly_top_trend = np.polyfit(xs_top, pruned_ys_top, deg=2)

T_y = np.polyval(poly_top_trend, xs_top)
T_y[0] = P_TL[1]
T_y[-1] = P_TR[1]
T_curve = np.column_stack((xs_top, T_y))

# 7. Left and Right Lateral polylines strictly along the mask boundary
ys_left = np.linspace(P_TL[1], P_BL[1], N_pts)
L_pts = []
for y in ys_left:
    y_int = int(np.clip(round(y), 0, h - 1))
    col_xs = np.where(mask[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        L_pts.append((float(col_xs[0]), y))
    else:
        L_pts.append((P_TL[0], y))
L_curve = np.array(L_pts)
L_curve[:, 0] = cv2.GaussianBlur(L_curve[:, 0].reshape(-1, 1), (5, 1), 1.0).ravel()
L_curve[0] = P_TL
L_curve[-1] = P_BL

ys_right = np.linspace(P_TR[1], P_BR[1], N_pts)
R_pts = []
for y in ys_right:
    y_int = int(np.clip(round(y), 0, h - 1))
    col_xs = np.where(mask[y_int, :] > 127)[0]
    if len(col_xs) > 0:
        R_pts.append((float(col_xs[-1]), y))
    else:
        R_pts.append((P_TR[0], y))
R_curve = np.array(R_pts)
R_curve[:, 0] = cv2.GaussianBlur(R_curve[:, 0].reshape(-1, 1), (5, 1), 1.0).ravel()
R_curve[0] = P_TR
R_curve[-1] = P_BR

# 8. Render Visual
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis)
green_layer[mask > 127] = [40, 225, 60]
vis_overlay = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)

# Blue lateral polylines
cv2.polylines(vis_overlay, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Green curves (smooth contour with teeth pruned!)
cv2.polylines(vis_overlay, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_overlay, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

h_vis, w_vis = vis_overlay.shape[:2]
zoom_bl = vis_overlay[int(h_vis*0.4):, :int(w_vis*0.6)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_smooth_pruned_overlay.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_zoom_smooth_pruned.png"), zoom_bl)

print("Saved barakiani_smooth_pruned_overlay.png and zoom!")
