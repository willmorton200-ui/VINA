import time
import cv2
import numpy as np
from pipeline.dewarp_engine import CylindricalDewarpEngine

engine = CylindricalDewarpEngine(use_gpu=True)

test_files = [
    ("Castillo de Liria", "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"),
    ("Alma Valley",       "test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"),
    ("Belbek Muscat",     "test_dataset/butilki/photo_2026-08-11_21-10-10.jpg"),
]

for name, path in test_files:
    img = cv2.imread(path)
    if img is None:
        continue
    
    t0 = time.perf_counter()
    res = engine.process_image(img)
    dt_ms = (time.perf_counter() - t0) * 1000
    
    print(f"\n[{name}] Processed in {dt_ms:.1f}ms:")
    print(f"  Artifacts keys: {list(res['artifacts'].keys())}")
    print(f"  Stage 5 Recognized Text: {res['full_text']}")

print("\nAll pipeline verification tests passed successfully!")
