import cv2
import numpy as np
import os

out_dir = r"D:\VINA\outputs\test_terra_restored\photo_2026-08-10_12-34-30 (3)"
crop = cv2.imread(os.path.join(out_dir, "stage1_retinex.png"))
mask = cv2.imread(os.path.join(out_dir, "stage1_mask.png"), cv2.IMREAD_GRAYSCALE)
dewarp = cv2.imread(os.path.join(out_dir, "flattened_image.png"))
annotated = cv2.imread(os.path.join(out_dir, "stage5_annotated.png"))
mesh = cv2.imread(os.path.join(out_dir, "stage3_mesh.png"))

vis = crop.copy()
mask_2d = mask > 127
green_layer = crop.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Draw contours
cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(vis, cnts, -1, (0, 0, 255), 2)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "terra_restored_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "terra_restored_dewarped.png"), dewarp)
cv2.imwrite(os.path.join(artifacts_dir, "terra_restored_annotated.png"), annotated)
cv2.imwrite(os.path.join(artifacts_dir, "terra_restored_mesh.png"), mesh)

print("Saved restored multi-label artifacts successfully!")
