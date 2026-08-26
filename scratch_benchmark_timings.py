import cv2
import glob
from pipeline.dewarp_engine import CylindricalDewarpEngine

engine = CylindricalDewarpEngine(use_gpu=True)

test_images = [
    "test_dataset/butilki/photo_2026-08-10_12-34-31.jpg", # Barakiani
    "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg", # Castillo de Liria
    "test_dataset/butilki/photo_2026-08-11_21-10-10.jpg", # Belbek
    "test_dataset/butilki/photo_2026-08-11_21-10-16.jpg", # Alma Valley
]

for path in test_images:
    img = cv2.imread(path)
    res = engine.process_image(img)
    t = res["timings"]
    print(f"=== {path} ===")
    print(f"  Stage 1 (YOLO + SAM + Preprocessing): {t['stage1_ms']} ms")
    print(f"  Stage 2 (Features & Vectorizer):       {t['stage2_ms']} ms")
    print(f"  Stage 3 (3D Mesh Optimization):        {t['stage3_ms']} ms")
    print(f"  Stage 4 (TPS Remapping & Lanczos-4):   {t['stage4_ms']} ms")
    print(f"  Stage 5 (OCR RapidOCR + EasyOCR):      {t['stage5_ms']} ms")
    print(f"  TOTAL TIME:                           {t['total_ms']} ms")
