import cv2
import numpy as np
import os
import json

out_dir = r"D:\VINA\outputs\test_barakiani_upright_integrated\photo_2026-08-10_12-34-31"
crop = cv2.imread(os.path.join(out_dir, "stage1_retinex.png"))
mask = cv2.imread(os.path.join(out_dir, "stage1_mask.png"), cv2.IMREAD_GRAYSCALE)
dewarp = cv2.imread(os.path.join(out_dir, "flattened_image.png"))
annotated = cv2.imread(os.path.join(out_dir, "stage5_annotated.png"))
mesh_vis = cv2.imread(os.path.join(out_dir, "stage3_mesh.png"))

with open(os.path.join(out_dir, "results.json"), "r", encoding="utf-8") as f:
    res = json.load(f)

print("Upright Integrated text tokens on Barakiani:")
for t in res.get("text_blocks", []):
    print(f"  - {t['text']} (conf: {t['confidence']*100:.1f}%)")

from pipeline.vectorizer import MaskVectorizer
vec = MaskVectorizer()
vm = vec.vectorize(mask)

P_TL = vm.P_TL
P_TR = vm.P_TR
P_BL = vm.P_BL
P_BR = vm.P_BR
L_curve = vm.L_line
R_curve = vm.R_line
T_curve = vm.T_curve
B_curve = vm.B_curve

vis = crop.copy()
mask_2d = mask > 127
green_layer = crop.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Central vertical axis
cx = int((P_TL[0] + P_TR[0] + P_BL[0] + P_BR[0]) / 4.0)
cv2.line(vis, (cx, 0), (cx, vis.shape[0] - 1), (0, 0, 255), 2, cv2.LINE_AA)

# Blue lateral polylines
cv2.polylines(vis, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Ellipsoid Green Curves
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

h_v, w_v = vis.shape[:2]
zoom_bl = vis[int(h_v*0.35):, :int(w_v*0.75)].copy()

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_upright_integrated_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_upright_integrated_zoom_bl.png"), zoom_bl)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_upright_integrated_mesh.png"), mesh_vis)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_upright_integrated_dewarped.png"), dewarp)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_upright_integrated_annotated.png"), annotated)

print("Saved all Barakiani upright integrated artifacts successfully!")
