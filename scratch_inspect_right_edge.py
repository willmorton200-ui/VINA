import cv2
import numpy as np

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

# Let's inspect the rightmost boundary points of the mask
for y in range(200, 600, 20):
    col_xs = np.where(crop_mask[y, :] > 127)[0]
    if len(col_xs) > 0:
        print(f"y = {y:3d}: x_left = {col_xs[0]:3d}, x_right = {col_xs[-1]:3d}, width = {col_xs[-1] - col_xs[0]:3d}")
