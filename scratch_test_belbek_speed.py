import time
import cv2
from pipeline.dewarp_engine import CylindricalDewarpEngine

img = cv2.imread("test_dataset/butilki/photo_2026-08-11_21-10-10.jpg")
engine = CylindricalDewarpEngine(use_gpu=True)

t0 = time.time()
res = engine.process_image(img)
total = time.time() - t0

t = res["timings"]
print("========================================")
print(f"NEW GPU ENGINE ON photo_2026-08-11_21-10-10.jpg:")
print(f"  1. Сегментация & Retinex: {t['stage1_ms']} ms")
print(f"  2. Линии & LSD:          {t['stage2_ms']} ms")
print(f"  3. 3D GCS Оптимизация:   {t['stage3_ms']} ms")
print(f"  4. GPU Dewarping:        {t['stage4_ms']} ms")
print(f"  5. OCR & Декодирование:  {t['stage5_ms']} ms")
print(f"  ИТОГО:                   {t['total_ms']} ms ({t['total_ms']/1000:.2f} сек)")
print("========================================")
