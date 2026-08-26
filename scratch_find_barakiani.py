import cv2
import os
import glob
from rapidocr_onnxruntime import RapidOCR

ocr = RapidOCR()
files = sorted(glob.glob("test_dataset/butilki/*.jpg"))

for f in files:
    img = cv2.imread(f)
    if img is None:
        continue
    # Run rapid ocr on small center crop
    h, w = img.shape[:2]
    crop = img[h//4: 3*h//4, w//4: 3*w//4]
    res, _ = ocr(crop)
    if res:
        texts = [r[1] for r in res]
        full = " ".join(texts)
        if "BARAKIANI" in full or "SAPERAVI" in full or "САПЕРАВИ" in full or "BARAKI" in full:
            print(f"FOUND BARAKIANI in: {f}")
            break
        elif "BAR" in full:
            print(f"Candidate: {f} -> {full[:60]}")
