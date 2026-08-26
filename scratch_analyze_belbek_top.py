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

print(f"P_TL={vm.P_TL}, P_TR={vm.P_TR}, P_BL={vm.P_BL}, P_BR={vm.P_BR}")

# Let's inspect the actual raw top boundary of the mask:
y_indices, x_indices = np.where(crop_mask > 127)
xs_top = np.linspace(vm.P_TL[0], vm.P_TR[0], 50)
raw_ys_top = []
for x in xs_top:
    col_ys = np.where(crop_mask[:, int(np.clip(round(x), 0, w - 1))] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_top.append(float(np.min(col_ys)))
    else:
        raw_ys_top.append(vm.P_TL[1])
raw_ys_top = np.array(raw_ys_top)

# Also bottom boundary:
xs_bot = np.linspace(vm.P_BL[0], vm.P_BR[0], 50)
raw_ys_bot = []
for x in xs_bot:
    col_ys = np.where(crop_mask[:, int(np.clip(round(x), 0, w - 1))] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_bot.append(float(np.max(col_ys)))
    else:
        raw_ys_bot.append(vm.P_BL[1])
raw_ys_bot = np.array(raw_ys_bot)

mid_idx = len(raw_ys_top) // 2
mid_span = int(len(raw_ys_top) * 0.15)
y_mid_top = float(np.median(raw_ys_top[mid_idx - mid_span : mid_idx + mid_span]))
y_corners_top = (vm.P_TL[1] + vm.P_TR[1]) / 2.0
delta_top = y_mid_top - y_corners_top

print(f"Top profile: y_corners={y_corners_top:.1f}, y_mid={y_mid_top:.1f}, delta_y = {delta_top:.1f} px")
if delta_top > 0:
    print("-> Top profile curves DOWNWARDS (smile / convex down) in perspective!")
else:
    print("-> Top profile curves UPWARDS (frown / convex up)!")

y_mid_bot = float(np.median(raw_ys_bot[mid_idx - mid_span : mid_idx + mid_span]))
y_corners_bot = (vm.P_BL[1] + vm.P_BR[1]) / 2.0
delta_bot = y_mid_bot - y_corners_bot
print(f"Bottom profile: y_corners={y_corners_bot:.1f}, y_mid={y_mid_bot:.1f}, delta_y = {delta_bot:.1f} px")

vis = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Current vectorizer output
cv2.polylines(vis, [vm.L_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vm.R_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

# Also draw the TRUE measured top curve following the mask in RED:
# True semi-ellipse with actual measured delta_top:
x0_top = (vm.P_TL[0] + vm.P_TR[0]) / 2.0
a_top = (vm.P_TR[0] - vm.P_TL[0]) / 2.0
theta = np.linspace(0.0, np.pi, 50)
T_true_x = x0_top - a_top * np.cos(theta)
# Real sagitta has sign of delta_top!
T_true_y = y_corners_top + delta_top * np.sin(theta) + (1.0 - theta / np.pi) * vm.P_TL[1] + (theta / np.pi) * vm.P_TR[1] - y_corners_top
T_true_y[0], T_true_y[-1] = vm.P_TL[1], vm.P_TR[1]
T_true_curve = np.column_stack((T_true_x, T_true_y))
cv2.polylines(vis, [T_true_curve.astype(np.int32)], False, (0, 0, 255), 4, cv2.LINE_AA)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "belbek_top_curve_analysis.png"), vis)
print("Saved belbek_top_curve_analysis.png successfully!")
