import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor

stage1 = Stage1Preprocessor(use_gpu=True)
img_bgr = cv2.imread("d:/VINA/test_dataset/butilki/tsimlyanskoe_krepost_sarkel.jpg")
cropped_bgr, cropped_mask, _ = stage1.segment_bottle_and_label(img_bgr)
print(f"cropped_bgr: {cropped_bgr.shape if cropped_bgr is not None else None}")
print(f"cropped_mask: {cropped_mask.shape if cropped_mask is not None else None}, NonZero: {np.sum(cropped_mask > 0) if cropped_mask is not None else 0}")

mask_after_gate = stage1._apply_photometric_paper_gate(cropped_bgr, cropped_mask)
print(f"mask_after_gate NonZero: {np.sum(mask_after_gate > 0) if mask_after_gate is not None else 0}")
