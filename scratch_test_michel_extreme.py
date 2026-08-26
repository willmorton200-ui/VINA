import cv2
import numpy as np

mask = cv2.imread("scratch_debug/michel_mask.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread("scratch_debug/michel_crop.png")
h, w = mask.shape[:2]

# 1. Clean mask to single largest component
binary = np.uint8(mask > 127)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask = np.zeros((h, w), dtype=np.uint8)
    clean_mask[labels == largest_label] = 255
    mask = clean_mask

# 2. Extract column-by-column top and bottom profiles
y_indices, x_indices = np.where(mask > 127)
x_min = int(np.min(x_indices))
x_max = int(np.max(x_indices))
y_min = int(np.min(y_indices))
y_max = int(np.max(y_indices))

xs = np.arange(x_min, x_max + 1)
ys_top_raw = []
ys_bot_raw = []

for x in xs:
    col_ys = np.where(mask[:, x] > 127)[0]
    if len(col_ys) > 0:
        ys_top_raw.append(float(np.min(col_ys)))
        ys_bot_raw.append(float(np.max(col_ys)))
    else:
        ys_top_raw.append(np.nan)
        ys_bot_raw.append(np.nan)

ys_top_raw = np.array(ys_top_raw)
ys_bot_raw = np.array(ys_bot_raw)

# Filter valid points
valid_top = ~np.isnan(ys_top_raw)
valid_bot = ~np.isnan(ys_bot_raw)

# 3. 4 Corner Points strictly on extreme outer boundary
P_TL = np.array([float(xs[valid_top][0]), float(ys_top_raw[valid_top][0])], dtype=np.float64)
P_TR = np.array([float(xs[valid_top][-1]), float(ys_top_raw[valid_top][-1])], dtype=np.float64)
P_BL = np.array([float(xs[valid_bot][0]), float(ys_bot_raw[valid_bot][0])], dtype=np.float64)
P_BR = np.array([float(xs[valid_bot][-1]), float(ys_bot_raw[valid_bot][-1])], dtype=np.float64)

# 4. Fit Smooth Top and Bottom Curves strictly through the extreme boundary points
poly_top = np.polyfit(xs[valid_top], ys_top_raw[valid_top], deg=2)
poly_bot = np.polyfit(xs[valid_bot], ys_bot_raw[valid_bot], deg=2)

N_samples = 30
xs_top_curve = np.linspace(P_TL[0], P_TR[0], N_samples)
ys_top_curve = np.polyval(poly_top, xs_top_curve)
ys_top_curve[0] = P_TL[1]
ys_top_curve[-1] = P_TR[1]
T_curve = np.column_stack((xs_top_curve, ys_top_curve))

xs_bot_curve = np.linspace(P_BL[0], P_BR[0], N_samples)
ys_bot_curve = np.polyval(poly_bot, xs_bot_curve)
ys_bot_curve[0] = P_BL[1]
ys_bot_curve[-1] = P_BR[1]
B_curve = np.column_stack((xs_bot_curve, ys_bot_curve))

# 5. Visualizations
vis = crop.copy()
mask_2d = mask > 127
green_layer = crop.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Blue Lateral Lines
cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green Curves
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)

# Red Central Axis
p_top_mid = (P_TL + P_TR) / 2.0
p_bot_mid = (P_BL + P_BR) / 2.0
for s in range(0, int(np.linalg.norm(p_bot_mid - p_top_mid)), 14):
    v_s = s / float(np.linalg.norm(p_bot_mid - p_top_mid))
    pt_a = (1.0 - v_s) * p_top_mid + v_s * p_bot_mid
    cv2.line(vis, (int(pt_a[0]), int(pt_a[1])), (int(pt_a[0]), int(pt_a[1] + 7)), (0, 0, 255), 2, cv2.LINE_AA)

# 4 Corner Green Dots
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

out_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\michel_extreme_points_vector.png"
cv2.imwrite(out_path, vis)

print("P_TL:", P_TL)
print("P_TR:", P_TR)
print("P_BL:", P_BL)
print("P_BR:", P_BR)
print(f"Saved {out_path} successfully!")
