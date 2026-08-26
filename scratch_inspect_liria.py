import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

stage1 = Stage1Preprocessor()
res = stage1.process(img_bgr)
cropped_bgr = res["cropped_bgr"]
cropped_mask = res["mask"]

os.makedirs("scratch_debug", exist_ok=True)
cv2.imwrite("scratch_debug/liria_crop.png", cropped_bgr)
cv2.imwrite("scratch_debug/liria_mask.png", cropped_mask)

print("Saved crop and mask for Castillo de Liria!")
print(f"Mask shape: {cropped_mask.shape}, nonzeros: {np.sum(cropped_mask > 127)}")
