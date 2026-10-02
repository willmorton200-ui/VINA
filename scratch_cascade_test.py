import cv2
import json
import os
import time
import base64
import numpy as np

from pipeline.catalog import WineCatalog
from pipeline.search_engine import WineSearchEngine
from pipeline.vina_studio_matcher import VinaStudioMatcher
from pipeline.color_matcher import calculate_visual_color_bonus
from pipeline import CylindricalDewarpEngine

def b64_to_img(b64_str):
    if not b64_str: return None
    if "," in b64_str: b64_str = b64_str.split(",")[1]
    img_data = base64.b64decode(b64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

print("Loading models...")
catalog = WineCatalog()
search_engine = WineSearchEngine(catalog, use_gpu=True)
vina_matcher = VinaStudioMatcher(catalog)
engine = CylindricalDewarpEngine(use_gpu=True)

img_path = r"D:\VINA\owner_eval\1\queries\e3f116c0.jpeg"
print(f"\nProcessing image: {img_path}")

img_bgr = cv2.imread(img_path)
t0 = time.time()

# 1. SigLIP Search
siglip_results = search_engine.search_by_cv2_image(img_bgr, top_k=5)

# 2. Dewarp & OCR
res = engine.process_image(img_bgr)
dewarped_b64 = res.get("artifacts", {}).get("dewarped")
dewarped_img = b64_to_img(dewarped_b64)

ocr_text = res.get("full_text", "")
print(f"\n--- OCR Text ---")
print(ocr_text)

# 3. SigLIP (Dewarped)
dewarped_results = []
if dewarped_img is not None:
    dewarped_results = search_engine.search_by_cv2_image(dewarped_img, top_k=5)

# 4. Combine & Sort
combined_scores = {}
for r in siglip_results:
    combined_scores[r["slug"]] = {"slug": r["slug"], "score": r["score"], "source": "raw"}
for r in dewarped_results:
    if r["slug"] not in combined_scores or r["score"] > combined_scores[r["slug"]]["score"]:
        combined_scores[r["slug"]] = {"slug": r["slug"], "score": r["score"], "source": "dewarped"}
        
sorted_candidates = sorted(combined_scores.values(), key=lambda x: x["score"], reverse=True)[:5]

# 5. Cascade Matcher (OCR Validation)
print("\n--- Running Cascade OCR Validation on Top 5 ---")
cascade_result = vina_matcher.cascade_decision(ocr_text, sorted_candidates)
best_slug = cascade_result["slug"]

# 6. Color Penalty
wine_info = catalog.get_wine(best_slug) or {}
color_bonus = 0.0
ref_path = wine_info.get("image_path")
if ref_path and os.path.exists(ref_path):
    ref_bgr = cv2.imread(ref_path)
    if dewarped_img is not None and ref_bgr is not None:
        color_bonus = calculate_visual_color_bonus(dewarped_img, ref_bgr)

print(f"\n--- Final Result ---")
print(f"Slug: {best_slug} ({wine_info.get('name')})")
print(f"Color Penalty: {color_bonus:.2f}")
print(f"Final Confidence: {cascade_result.get('final_confidence') + color_bonus:.2f}%")

print("\n--- Detailed Candidate List ---")
for c in cascade_result.get("candidates", []):
    c_info = catalog.get_wine(c['slug']) or {}
    c_bonus = 0.0
    c_path = c_info.get("image_path")
    if c_path and os.path.exists(c_path):
        c_bgr = cv2.imread(c_path)
        if dewarped_img is not None and c_bgr is not None:
            c_bonus = calculate_visual_color_bonus(dewarped_img, c_bgr)
    
    print(f"[{c['slug']}] EmbConf: {c['confidence_embedding']:.2f} | OCR Bonus: {c['ocr_bonus']:.2f} | Color Penalty: {c_bonus:.2f} | Final: {c['final_confidence'] + c_bonus:.2f}% (Matches: {c['match_count']})")

