import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

rapid_ocr = RapidOCR()

images = [
    ("Michel Schneider", r"D:\VINA\outputs\test_michel_extreme\photo_2026-08-10_12-34-30 (2)\flattened_image.png"),
    ("Alma Valley", r"D:\VINA\outputs\test_exact_mask_pipeline\photo_2026-08-11_21-10-16\flattened_image.png"),
    ("Castillo de Liria", r"D:\VINA\outputs\test_liria_corrected\photo_2026-08-10_12-34-29\flattened_image.png"),
    ("Крепость Саркел", r"D:\VINA\outputs\test_bottle_21_10_07\photo_2026-08-11_21-10-07\flattened_image.png")
]

for title, img_path in images:
    print(f"\n=======================================================")
    print(f"Testing RapidOCR on: {title}")
    print(f"=======================================================")
    img = cv2.imread(img_path)
    if img is None:
        print("Image not found:", img_path)
        continue
        
    result, elapse = rapid_ocr(img)
    if result:
        for idx, item in enumerate(result, 1):
            bbox, text, score = item
            print(f"[{idx:02d}] {text:<35} | Точность: {score*100.0:5.1f}%")
    else:
        print("No text detected.")
