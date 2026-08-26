import cv2
import numpy as np
import os
import json

out_dir = r"D:\VINA\outputs\test_alma_restored_clean\photo_2026-08-11_21-10-16"
crop = cv2.imread(os.path.join(out_dir, "stage1_retinex.png"))
mask = cv2.imread(os.path.join(out_dir, "stage1_mask.png"), cv2.IMREAD_GRAYSCALE)
dewarp = cv2.imread(os.path.join(out_dir, "flattened_image.png"))
annotated = cv2.imread(os.path.join(out_dir, "stage5_annotated.png"))
mesh_vis = cv2.imread(os.path.join(out_dir, "stage3_mesh.png"))

from pipeline.vectorizer import MaskVectorizer
vec = MaskVectorizer()
vm = vec.vectorize(mask)

P_TL = vm.P_TL
P_TR = vm.P_TR
P_BL = vm.P_BL
P_BR = vm.P_BR

# Semitransparent Greenish Overlay
vis = crop.copy()
mask_2d = mask > 127
green_layer = crop.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Blue lateral lines
cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green curves
cv2.polylines(vis, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "alma_verified_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "alma_verified_mask.png"), mask)
cv2.imwrite(os.path.join(artifacts_dir, "alma_verified_mesh.png"), mesh_vis)
cv2.imwrite(os.path.join(artifacts_dir, "alma_verified_dewarped.png"), dewarp)
cv2.imwrite(os.path.join(artifacts_dir, "alma_verified_annotated.png"), annotated)

print("Saved all Alma Valley verified report artifacts successfully!")
