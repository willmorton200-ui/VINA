import cv2
import numpy as np
import os
import matplotlib.pyplot as plt

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

print(f"Crop shape: {crop_bgr.shape}, Bbox info: {bbox_info}")

# Save the original uncropped image with bbox
vis_full = img_bgr.copy()
bx0, by0 = bbox_info["crop_x"], bbox_info["crop_y"]
bw, bh = bbox_info["crop_w"], bbox_info["crop_h"]
cv2.rectangle(vis_full, (bx0, by0), (bx0 + bw, by0 + bh), (0, 255, 0), 3)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "castillo_full_detection_bbox.png"), vis_full)

# Save high-res crop and mask side-by-side
mask_bgr = cv2.cvtColor(crop_mask, cv2.COLOR_GRAY2BGR)
side_by_side = np.hstack((crop_bgr, mask_bgr))
cv2.imwrite(os.path.join(artifacts_dir, "castillo_crop_and_mask.png"), side_by_side)

# Inspect the right boundary of the white label vs mask
# Let's find where the white paper label ends on the right using color/edge thresholding
gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray, 50, 150)

# Overlay mask on crop
mask_overlay = crop_bgr.copy()
mask_overlay[crop_mask > 127] = cv2.addWeighted(crop_bgr[crop_mask > 127], 0.5, np.full_like(crop_bgr[crop_mask > 127], (40, 240, 60)), 0.5, 0)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_mask_overlay_detailed.png"), mask_overlay)

print("Saved detailed inspection images successfully!")
