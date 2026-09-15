import cv2
import numpy as np
from pipeline.sam_refiner import SAMRefiner

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-09.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

box0 = [211, 875, 1013, 1848]
sam = SAMRefiner(model_type="vit_h")
sam_mask, score = sam.refine_mask(img_bgr, box0)

# Check non-zero bbox of sam_mask
coords = cv2.findNonZero(sam_mask)
x_min, x_max = int(np.min(coords[:, 0, 0])), int(np.max(coords[:, 0, 0]))
y_min, y_max = int(np.min(coords[:, 0, 1])), int(np.max(coords[:, 0, 1]))

print(f"SAM mask non-zero bounds: x=[{x_min}, {x_max}] (w={x_max - x_min}), y=[{y_min}, {y_max}] (h={y_max - y_min})")
print(f"Input box: {box0}")
cv2.imwrite("scratch_debug/photo09_sam_mask.png", sam_mask)
