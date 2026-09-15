import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

stage1 = Stage1Preprocessor(use_gpu=True)
img_bgr = cv2.imread("d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-16.jpg")
crop_bgr, crop_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)

print("bbox_info:", bbox_info)

# Let's inspect where the corners in vector_mask are!
vec = bbox_info["vector_mask"]
print(f"vec P_TL: {vec.P_TL}, P_TR: {vec.P_TR}, P_BL: {vec.P_BL}, P_BR: {vec.P_BR}")

# Let's check why MaskVectorizer extracted P_TL at y=494 on crop_mask
vectorizer = MaskVectorizer()
vec2 = vectorizer.vectorize(crop_mask)
print(f"vec2 P_TL: {vec2.P_TL}, P_TR: {vec2.P_TR}")
