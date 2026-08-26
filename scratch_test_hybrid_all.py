import cv2
import numpy as np
from scratch_test_hybrid_ocr import EnhancedOCRDecoder

decoder = EnhancedOCRDecoder(use_gpu=True)

test_labels = [
    ("Alma Valley", r"D:\VINA\outputs\test_exact_mask_pipeline\photo_2026-08-11_21-10-16\flattened_image.png"),
    ("Castillo de Liria", r"D:\VINA\outputs\test_liria_corrected\photo_2026-08-10_12-34-29\flattened_image.png"),
    ("Крепость Саркел", r"D:\VINA\outputs\test_bottle_21_10_07\photo_2026-08-11_21-10-07\flattened_image.png")
]

for title, path in test_labels:
    print(f"\n=======================================================")
    print(f"HYBRID OCR: {title}")
    print(f"=======================================================")
    img = cv2.imread(path)
    blocks = decoder.extract_text(img)
    for idx, b in enumerate(blocks, 1):
        print(f"[{idx:02d}] {b['text']:<35} | Точность: {b['confidence']*100.0:5.1f}%")
