import cv2
import numpy as np
import os
from pipeline.vectorizer import MaskVectorizer

brain_dir = "C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/tsimlyanskoe_step_by_step"
crop_mask = cv2.imread(os.path.join(brain_dir, "step2_sam_mask.png"), cv2.IMREAD_GRAYSCALE)
crop_bgr = cv2.imread(os.path.join(brain_dir, "step2_sam_overlay.png")) # or raw crop
h_c, w_c = crop_mask.shape[:2]

# Use MaskVectorizer to find the true 4 corner vertices
vectorizer = MaskVectorizer()
vec = vectorizer.vectorize(crop_mask)

P_TL = vec.P_TL
P_TR = vec.P_TR
P_BL = vec.P_BL
P_BR = vec.P_BR

print(f"P_TL: {P_TL}, P_TR: {P_TR}")
print(f"P_BL: {P_BL}, P_BR: {P_BR}")

# 2 Straight Lateral Guides (connecting top and bottom corner vertices)
N_pts = 64
v_vals = np.linspace(0.0, 1.0, N_pts)
L_line = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
R_line = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR

# 5 Control Points on Top Boundary
# Find mask top edge at 5 equally spaced X locations between P_TL[0] and P_TR[0]
u_5 = np.linspace(0.0, 1.0, 5)
top_5_pts = []
for u in u_5:
    x_target = int(round((1.0 - u) * P_TL[0] + u * P_TR[0]))
    x_target = np.clip(x_target, 0, w_c - 1)
    ys = np.where(crop_mask[:, x_target] > 127)[0]
    if len(ys) > 0:
        top_5_pts.append((float(x_target), float(ys[0])))
    else:
        # Interpolate between corners
        y_int = (1.0 - u) * P_TL[1] + u * P_TR[1]
        top_5_pts.append((float(x_target), float(y_int)))
top_5_pts = np.array(top_5_pts)
top_5_pts[0] = P_TL
top_5_pts[-1] = P_TR

# 5 Control Points on Bottom Boundary
bot_5_pts = []
for u in u_5:
    x_target = int(round((1.0 - u) * P_BL[0] + u * P_BR[0]))
    x_target = np.clip(x_target, 0, w_c - 1)
    ys = np.where(crop_mask[:, x_target] > 127)[0]
    if len(ys) > 0:
        bot_5_pts.append((float(x_target), float(ys[-1])))
    else:
        y_int = (1.0 - u) * P_BL[1] + u * P_BR[1]
        bot_5_pts.append((float(x_target), float(y_int)))
bot_5_pts = np.array(bot_5_pts)
bot_5_pts[0] = P_BL
bot_5_pts[-1] = P_BR

# Smooth the 5-point polylines into 2 continuous horizontal guide curves
u_dense = np.linspace(0.0, 1.0, N_pts)
poly_T = np.polyfit(u_5, top_5_pts[:, 1], deg=2)
poly_B = np.polyfit(u_5, bot_5_pts[:, 1], deg=2)

T_curve = np.column_stack((
    (1.0 - u_dense) * P_TL[0] + u_dense * P_TR[0],
    np.polyval(poly_T, u_dense)
))
T_curve[0] = P_TL
T_curve[-1] = P_TR

B_curve = np.column_stack((
    (1.0 - u_dense) * P_BL[0] + u_dense * P_BR[0],
    np.polyval(poly_B, u_dense)
))
B_curve[0] = P_BL
B_curve[-1] = P_BR

# Load clean raw crop
raw_crop_path = "d:/VINA/test_dataset/butilki/tsimlyanskoe_krepost_sarkel.jpg"
full_img = cv2.imread(raw_crop_path)
coords = cv2.findNonZero(cv2.imread(os.path.join(brain_dir, "step2_sam_mask.png"), cv2.IMREAD_GRAYSCALE))
# we can read crop_bgr directly
vis = crop_bgr.copy()

# Draw 5-point polyline (thin yellow)
cv2.polylines(vis, [top_5_pts.astype(np.int32)], False, (0, 255, 255), 1, cv2.LINE_AA)
cv2.polylines(vis, [bot_5_pts.astype(np.int32)], False, (0, 255, 255), 1, cv2.LINE_AA)

# Draw 2 horizontal smoothed guide curves (thick green)
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)

# Draw 2 straight lateral guides (thick blue)
cv2.polylines(vis, [L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)

# Draw the 5 points (cyan circles)
for pt in top_5_pts:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 5, (255, 255, 0), -1, cv2.LINE_AA)
for pt in bot_5_pts:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 5, (255, 255, 0), -1, cv2.LINE_AA)

# Draw the 4 corner vertices (red with white border)
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)

cv2.imwrite(os.path.join(brain_dir, "step3_fixed_guides.png"), vis)
print("Saved step3_fixed_guides.png!")
