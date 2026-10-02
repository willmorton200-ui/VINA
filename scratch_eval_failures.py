import json
import cv2
import os
from pipeline.search_engine import WineSearchEngine

from pipeline.catalog import WineCatalog
from pipeline.vina_studio_matcher import VinaStudioMatcher
from pipeline import CylindricalDewarpEngine
from pipeline.color_matcher import calculate_structural_orb_matches

import numpy as np
import base64

def b64_to_img(b64_str):
    if not b64_str: return None
    if "," in b64_str:
        b64_str = b64_str.split(",")[1]
    b = base64.b64decode(b64_str)
    n = np.frombuffer(b, np.uint8)
    return cv2.imdecode(n, cv2.IMREAD_COLOR)

def run_eval():
    golden_path = r"D:\VINA\owner_eval\1\mapping.json"
    with open(golden_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        queries = data if isinstance(data, list) else data.get("cases", [])
        if not queries:
            # Maybe it's a list directly
            pass

    # Actually, in owner_eval/1/mapping.json, it's usually a list of dicts.
    
    catalog = WineCatalog()
    matcher = VinaStudioMatcher(catalog)
    search_engine = WineSearchEngine(catalog, r"D:\VINA\models\siglip2_index.faiss")
    engine = CylindricalDewarpEngine(use_gpu=True)
    
    failed = 0
    total = 0
    
    for q in queries:
        total += 1
        img_path = os.path.join(r"D:\VINA\owner_eval\1\queries", q["image_path"])
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            print(f"Failed to load {img_path}")
            continue
            
        vina_result = engine.process_image(img_bgr)
        ocr_text = vina_result.get("full_text", "")
        siglip_results = search_engine.search_by_cv2_image(img_bgr, top_k=5)
        decision = matcher.cascade_decision(ocr_text, siglip_results)
        
        candidates = decision.get("candidates", [])
        candidates.sort(key=lambda x: x["raw_final_confidence"] if "raw_final_confidence" in x else x["final_confidence"], reverse=True)
        
        if candidates:
            decision["slug"] = candidates[0]["slug"]        
        expected = q["expected_slug"]
        predicted = decision["slug"]
        
        if expected != predicted:
            failed += 1
            print(f"\n--- FAILED: {q['image_path']} ---")
            print(f"OCR TEXT: {ocr_text.strip()}")
            print(f"EXPECTED: {expected}")
            print(f"PREDICTED: {predicted}")
            for i, c in enumerate(decision["candidates"][:3]):
                print(f"  {i+1}. {c['slug']} | emb: {c['confidence_embedding']} | final: {c['final_confidence']}")

    print(f"\nTotal Failed: {failed} out of {total} (Acc: {(total-failed)/total*100:.1f}%)")

if __name__ == "__main__":
    run_eval()
