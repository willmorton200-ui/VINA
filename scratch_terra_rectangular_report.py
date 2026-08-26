import cv2
import numpy as np
import os
import json

out_dir = r"D:\VINA\outputs\test_terra_rectangular\photo_2026-08-10_12-34-30 (3)"
crop = cv2.imread(os.path.join(out_dir, "stage1_retinex.png"))
mask = cv2.imread(os.path.join(out_dir, "stage1_mask.png"), cv2.IMREAD_GRAYSCALE)
dewarp = cv2.imread(os.path.join(out_dir, "flattened_image.png"))
annotated = cv2.imread(os.path.join(out_dir, "stage5_annotated.png"))
mesh_vis = cv2.imread(os.path.join(out_dir, "stage3_mesh.png"))

with open(os.path.join(out_dir, "results.json"), "r", encoding="utf-8") as f:
    res = json.load(f)

print("Recognized text tokens on rectangular label:")
for t in res.get("text_blocks", []):
    print(f"  - {t['text']} (conf: {t['confidence']*100:.1f}%)")

# Semitransparent Greenish Overlay
vis = crop.copy()
mask_2d = mask > 127
green_layer = crop.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "terra_rectangular_mask.png"), mask)
cv2.imwrite(os.path.join(artifacts_dir, "terra_rectangular_overlay.png"), vis)
cv2.imwrite(os.path.join(artifacts_dir, "terra_rectangular_dewarped.png"), dewarp)
cv2.imwrite(os.path.join(artifacts_dir, "terra_rectangular_annotated.png"), annotated)
cv2.imwrite(os.path.join(artifacts_dir, "terra_rectangular_mesh.png"), mesh_vis)

print("Saved all Terra Argenta rectangular label artifacts successfully!")
