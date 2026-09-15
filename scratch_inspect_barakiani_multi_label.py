import cv2
import numpy as np
import os

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')

# 1. Upper Label alone: [239, 366, 673, 685]
mask_upper, _ = p1.sam_refiner.refine_mask(img, [239, 366, 673, 685])
crop_upper = img[350:700, 220:690].copy()
mask_crop_upper = mask_upper[350:700, 220:690].copy()

# 2. Lower Label alone: [241, 670, 654, 1115]
mask_lower, _ = p1.sam_refiner.refine_mask(img, [241, 670, 654, 1115])
crop_lower = img[660:1130, 220:670].copy()
mask_crop_lower = mask_lower[660:1130, 220:670].copy()

def overlay_m(crop, mask, col=(0, 255, 0)):
    vis = crop.copy()
    vis[mask > 127] = cv2.addWeighted(crop[mask > 127], 0.5, np.full_like(crop[mask > 127], col), 0.5, 0)
    cnts, _ = cv2.findContours(np.uint8(mask > 127)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(vis, cnts, -1, (255, 255, 255), 2)
    return vis

vis_up = overlay_m(crop_upper, mask_crop_upper, (0, 255, 0))
vis_low = overlay_m(crop_lower, mask_crop_lower, (0, 255, 0))

cv2.imwrite(os.path.join(artifacts_dir, "barakiani_upper_label_mask.png"), vis_up)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_lower_label_mask.png"), vis_low)

print("Saved upper and lower mask overlays to artifacts.")
