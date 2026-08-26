import cv2
import numpy as np
import os
import json

out_dir = r"D:\VINA\outputs\test_barakiani_robust_vector\photo_2026-08-10_12-34-31"
crop = cv2.imread(os.path.join(out_dir, "stage1_retinex.png"))
mask = cv2.imread(os.path.join(out_dir, "stage1_mask.png"), cv2.IMREAD_GRAYSCALE)
dewarp = cv2.imread(os.path.join(out_dir, "flattened_image.png"))
annotated = cv2.imread(os.path.join(out_dir, "stage5_annotated.png"))
mesh_vis = cv2.imread(os.path.join(out_dir, "stage3_mesh.png"))

with open(os.path.join(out_dir, "results.json"), "r", encoding="utf-8") as f:
    res = json.load(f)

print("Recognized text tokens on Barakiani:")
for t in res.get("text_blocks", []):
    print(f"  - {t['text']} (conf: {t['confidence']*100:.1f}%)")

from pipeline.vectorizer import MaskVectorizer
vec = MaskVectorizer()
vm = vec.vectorize(mask)

P_TL = vm.P_TL
P_TR = vm.P_TR
P_BL = vm.P_BL
P_BR = vm.P_BR

# 1. Overlay on raw Mask
vis_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
green_layer = np.zeros_like(vis_mask)
green_layer[mask > 127] = [40, 225, 60]
vis_mask_overlay = cv2.addWeighted(vis_mask, 0.60, green_layer, 0.40, 0)

# Blue lateral lines
cv2.line(vis_mask_overlay, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis_mask_overlay, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green curves
cv2.polylines(vis_mask_overlay, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_mask_overlay, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_mask_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mask_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# 2. Overlay on Color Crop
vis_color = crop.copy()
vis_color[mask > 127] = cv2.addWeighted(crop[mask > 127], 0.65, green_layer[mask > 127], 0.35, 0)
cv2.line(vis_color, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis_color, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_color, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_color, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_color, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_color, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_verified_mask_overlay.png"), vis_mask_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_verified_color_overlay.png"), vis_color)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_verified_mesh.png"), mesh_vis)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_verified_dewarped.png"), dewarp)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_verified_annotated.png"), annotated)

print("Saved all Barakiani verified report artifacts successfully!")
