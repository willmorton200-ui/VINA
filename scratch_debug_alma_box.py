import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
crop_bgr, crop_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)

# Save the stage1 result
os.makedirs("scratch_debug/alma_box", exist_ok=True)
cv2.imwrite("scratch_debug/alma_box/crop_bgr.png", crop_bgr)
cv2.imwrite("scratch_debug/alma_box/crop_mask.png", crop_mask)

# Vectorize
vectorizer = MaskVectorizer()
vec = vectorizer.vectorize(crop_mask)

vis = crop_bgr.copy()
cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite("scratch_debug/alma_box/vector_features.png", vis)

print("Saved scratch_debug/alma_box/vector_features.png!")
print(f"P_TL={vec.P_TL}, P_TR={vec.P_TR}, P_BL={vec.P_BL}, P_BR={vec.P_BR}")
