import sys
sys.path.append('d:/VINA')

import cv2
import time
from pipeline.dewarp_engine import CylindricalDewarpEngine

img_path = r'd:\VINA\owner_eval\119\queries\29afa3fa-4330-4cfa-814e-7c7779053510.jpg'
img_bgr = cv2.imread(img_path)
if img_bgr is None:
    print("Could not read image")
    sys.exit(1)

print("--- STAGE 1: Preprocessing (YOLO) ---")
engine = CylindricalDewarpEngine(use_gpu=True)
t0 = time.time()
cropped_bgr, cropped_mask, _ = engine.stage1.segment_bottle_and_label(img_bgr)
print(f"Time: {time.time()-t0:.2f}s")
if cropped_mask is not None:
    print(f"Mask found. Shape: {cropped_mask.shape}")
else:
    print("No mask found!")

print("\n--- STAGE 2-4: Dewarping ---")
t0 = time.time()
res = engine._dewarp_single_tier(cropped_bgr, cropped_mask)
print(f"Time: {time.time()-t0:.2f}s")
print(f"Rectified shape: {res['dewarped'].shape}")

print("\n--- STAGE 5: OCR (Already run in DewarpEngine) ---")
ocr_result = res["ocr_dew"]
print("OCR full text:", repr(ocr_result["full_text"]))

print("\n--- FINAL EMBEDDING MATCH ---")
from pipeline.search_engine import SearchEngine
search = SearchEngine(use_gpu=True)
t0 = time.time()
siglip_results = search.search_by_cv2_image(img_bgr, top_k=5)
print(f"Time: {time.time()-t0:.2f}s")
for i, r in enumerate(siglip_results):
    print(f"{i+1}: {r['slug']} - {r['score']}")

