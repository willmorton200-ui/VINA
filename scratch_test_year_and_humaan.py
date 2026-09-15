import cv2
import numpy as np
import os
from rapidocr_onnxruntime import RapidOCR
from pipeline.wine_lexicon_corrector import WineVocabularyCorrector
from pipeline.dewarp_engine import CylindricalDewarpEngine

# 1. Test image
img_path = 'd:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-09.jpg'
img_bgr = cv2.imread(img_path)

engine = CylindricalDewarpEngine()
res = engine.process_image(img_bgr)
dewarped = res['comparison']['dewarped']['image'] # or dewarped numpy

# Let's get dewarped numpy directly
cropped_bgr, cropped_mask, _ = engine.stage1.segment_bottle_and_label(img_bgr)
vec = engine.vectorizer.vectorize(cropped_mask)
dew_res = engine._dewarp_single_tier(cropped_bgr, cropped_mask)
dew_img = dew_res['dewarped']

# Test OCR with different unsharp mask / CLAHE enhancement
def enhance_label_for_ocr(img):
    # 1. Convert to LAB and apply CLAHE to L channel
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enh = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge([l_enh, a, b]), cv2.COLOR_LAB2BGR)
    
    # 2. Subtle unsharp mask
    gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    sharpened = cv2.addWeighted(enhanced, 1.4, gaussian, -0.4, 0)
    return sharpened

enh_img = enhance_label_for_ocr(dew_img)

# Compare RapidOCR with det_unclip_ratio=1.8 vs default
ocr_std = RapidOCR()
ocr_tuned = RapidOCR(det_unclip_ratio=1.9, det_db_box_thresh=0.4)

res_std, _ = ocr_std(dew_img)
res_enh, _ = ocr_std(enh_img)
res_tuned, _ = ocr_tuned(enh_img)

print("Standard OCR on raw dewarped:")
if res_std:
    for b in res_std:
        print(f"  {b[1]} (conf: {b[2]:.2f})")

print("\nStandard OCR on Enhanced / Sharpened dewarped:")
if res_enh:
    for b in res_enh:
        print(f"  {b[1]} (conf: {b[2]:.2f})")

print("\nTuned OCR (unclip=1.9) on Enhanced dewarped:")
if res_tuned:
    for b in res_tuned:
        print(f"  {b[1]} (conf: {b[2]:.2f})")

# Test lexicon correction with context
lexicon = WineVocabularyCorrector()
raw_texts = [b[1] for b in (res_tuned or res_enh or res_std or [])]
print(f"\nRaw tokens: {raw_texts}")

full_raw = " ".join(raw_texts)
cor_text, cor_logs = lexicon.correct_text(full_raw)
print(f"Corrected Full Text: '{cor_text}'")
print(f"Corrections log: {cor_logs}")
