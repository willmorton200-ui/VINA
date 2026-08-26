import cv2
import numpy as np
import os
import torch

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-30 (3).jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

from pipeline.sam_refiner import SAMRefiner
sam = SAMRefiner()

# Box 1: Upper label "TERRA ARGENTA" [463, 482, 779, 767]
box_upper = [463, 482, 779, 767]
mask_upper, score_upper = sam.refine_mask(img_bgr, box_upper)

# Box 2: Lower label "ARGENTINA MALBEC" [528, 815, 711, 1067]
box_lower = [528, 815, 711, 1067]
mask_lower, score_lower = sam.refine_mask(img_bgr, box_lower)

# Combined mask of both labels on the central bottle
combined_mask = np.maximum(mask_upper, mask_lower)

# Visual overlay
vis = img_bgr.copy()
green_upper = np.zeros_like(vis)
green_upper[mask_upper > 127] = [40, 225, 60]
vis[mask_upper > 127] = cv2.addWeighted(img_bgr[mask_upper > 127], 0.5, green_upper[mask_upper > 127], 0.5, 0)

green_lower = np.zeros_like(vis)
green_lower[mask_lower > 127] = [0, 200, 255]
vis[mask_lower > 127] = cv2.addWeighted(img_bgr[mask_lower > 127], 0.5, green_lower[mask_lower > 127], 0.5, 0)

# Draw contours
cnts_up, _ = cv2.findContours(mask_upper, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cnts_low, _ = cv2.findContours(mask_lower, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(vis, cnts_up, -1, (0, 0, 255), 3)
cv2.drawContours(vis, cnts_low, -1, (0, 0, 255), 3)

os.makedirs("scratch_debug", exist_ok=True)
cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\terra_sam_both_labels.png", vis)
cv2.imwrite("scratch_debug/terra_mask_upper.png", mask_upper)
cv2.imwrite("scratch_debug/terra_mask_lower.png", mask_lower)
cv2.imwrite("scratch_debug/terra_combined_mask.png", combined_mask)

print("Saved terra_sam_both_labels.png successfully!")
