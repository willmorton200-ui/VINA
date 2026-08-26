import cv2
import numpy as np

# Load mask and color crop
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# 4 Corner Points
P_TL = np.array([111.0, 157.0], dtype=np.float64)
P_TR = np.array([660.0, 175.0], dtype=np.float64)
P_BL = np.array([49.0, 1496.0], dtype=np.float64)
P_BR = np.array([626.0, 1496.0], dtype=np.float64)

# Top and Bottom Curves
xs_top = np.linspace(P_TL[0], P_TR[0], 28)
ys_top = []
for x in xs_top:
    x_int = int(np.clip(x, 0, w - 1))
    ys = np.where(mask[:, x_int] > 127)[0]
    ys_top.append(float(np.min(ys)) if len(ys) > 0 else P_TL[1])
poly_top = np.polyfit(xs_top, ys_top, deg=2)
T_x = xs_top
T_y = np.polyval(poly_top, T_x)
T_y[0] = P_TL[1]
T_y[-1] = P_TR[1]
T_curve = np.column_stack((T_x, T_y))

xs_bot = np.linspace(P_BL[0], P_BR[0], 28)
ys_bot = []
for x in xs_bot:
    x_int = int(np.clip(x, 0, w - 1))
    ys = np.where(mask[:, x_int] > 127)[0]
    ys_bot.append(float(np.max(ys)) if len(ys) > 0 else P_BL[1])
poly_bot = np.polyfit(xs_bot, ys_bot, deg=2)
B_x = xs_bot
B_y = np.polyval(poly_bot, B_x)
B_y[0] = P_BL[1]
B_y[-1] = P_BR[1]
B_curve = np.column_stack((B_x, B_y))

# -------------------------------------------------------------
# 1. CREATE SEMITRANSPARENT GREENISH MASK OVERLAY
# -------------------------------------------------------------
vis = crop.copy()
mask_bool = mask > 127

# Greenish tint (BGR: [30, 220, 50])
green_layer = np.zeros_like(vis)
green_layer[mask_bool] = [40, 225, 60]

# Alpha blending over mask region: 35% green tint + 65% bottle photo
alpha = 0.35
vis[mask_bool] = cv2.addWeighted(crop[mask_bool], 1.0 - alpha, green_layer[mask_bool], alpha, 0)

# -------------------------------------------------------------
# 2. DRAW VECTOR GEOMETRY ON TOP
# -------------------------------------------------------------
# Blue Side Boundary Lines
cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green Top and Bottom Boundary Curves
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)

# Green Top Chord connecting P_TL and P_TR
cv2.line(vis, (int(P_TL[0] - 25), int(P_TL[1] - 3)), (int(P_TR[0] + 25), int(P_TR[1] + 3)), (0, 255, 0), 2, cv2.LINE_AA)

# Central Axis (Red dashed line connecting midpoints)
p_top_mid = (P_TL + P_TR) / 2.0
p_bot_mid = (P_BL + P_BR) / 2.0
for s in range(0, int(np.linalg.norm(p_bot_mid - p_top_mid)), 14):
    v_s = s / float(np.linalg.norm(p_bot_mid - p_top_mid))
    pt_a = (1.0 - v_s) * p_top_mid + v_s * p_bot_mid
    cv2.line(vis, (int(pt_a[0]), int(pt_a[1])), (int(pt_a[0]), int(pt_a[1] + 7)), (0, 0, 255), 2, cv2.LINE_AA)

# 4 Corner Green Dots strictly on mask boundary
for pt, name in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

out_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\semitransparent_mask_vector_overlay.png"
cv2.imwrite(out_path, vis)
print("Saved semitransparent_mask_vector_overlay.png with greenish tint successfully!")
