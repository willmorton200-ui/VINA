import os
import cv2
import time
import base64
import numpy as np

from pipeline.catalog import WineCatalog
from pipeline.search_engine import WineSearchEngine
from pipeline.vina_studio_matcher import VinaStudioMatcher
from pipeline.dewarp_engine import CylindricalDewarpEngine

print("Loading models...")
catalog = WineCatalog(r"D:\VINA\wines_integrated_clean.csv")
search_engine = WineSearchEngine(catalog, r"D:\VINA\models\siglip2_index.faiss")
vina_matcher = VinaStudioMatcher(catalog)
engine = CylindricalDewarpEngine(use_gpu=True)

img_path = r"D:\Eval\queries\eval_photo_029.webp"
print(f"Processing: {img_path}")

img_bgr = cv2.imread(img_path)
if img_bgr is None:
    print("Error loading image")
    exit(1)

def b64_to_img(b64_str):
    if not b64_str: return None
    if "," in b64_str:
        b64_str = b64_str.split(",")[1]
    b = base64.b64decode(b64_str)
    n = np.frombuffer(b, np.uint8)
    return cv2.imdecode(n, cv2.IMREAD_COLOR)

vina_result = engine.process_image(img_bgr)
ocr_text = vina_result.get("full_text", "")

dewarped_b64 = vina_result.get("artifacts", {}).get("dewarped")
dewarped_img = b64_to_img(dewarped_b64)

siglip_results = search_engine.search_by_cv2_image(img_bgr, top_k=5)
dewarped_results = []
if dewarped_img is not None:
    dewarped_results = search_engine.search_by_cv2_image(dewarped_img, top_k=5)
    
combined_scores = {}
for r in siglip_results:
    combined_scores[r["slug"]] = {"slug": r["slug"], "score": r["score"]}
for r in dewarped_results:
    if r["slug"] not in combined_scores or r["score"] > combined_scores[r["slug"]]["score"]:
        combined_scores[r["slug"]] = {"slug": r["slug"], "score": r["score"]}
        
sorted_candidates = sorted(combined_scores.values(), key=lambda x: x["score"], reverse=True)[:5]
cascade_result = vina_matcher.cascade_decision(ocr_text, sorted_candidates)
candidates = cascade_result.get("candidates", [])

report_md = f"### Распознанный текст (OCR)\n```text\n{ocr_text.strip()}\n```\n\n### Топ-5 кандидатов\n\n"
for c in sorted(candidates, key=lambda x: x.get("final_confidence", 0), reverse=True):
    report_md += f"- **[{c.get('name', '')}]** {c.get('slug', '')}\n"
    report_md += f"   - Базовая уверенность (Embedding): {c.get('confidence_embedding', 0.0):.2f}%\n"
    report_md += f"   - OCR Бонус/Штраф: {c.get('ocr_bonus', 0.0):.2f}\n"
    report_md += f"   - Совпадений слов (Match Count): {c.get('match_count', 0)} из {c.get('total_words', 0)}\n"
    report_md += f"   - Совпавшие слова: {c.get('matched_words', [])}\n"
    report_md += f"   - **Итого Уверенность**: {c.get('final_confidence', 0.0):.2f}%\n\n"

out_path = r"C:\Users\User\.gemini\antigravity-ide\brain\87775b34-5873-41dc-9759-c68cb81d69e1\eval_photo_029_report.md"
with open(out_path, "w", encoding="utf-8") as f:
    f.write(report_md)
print(f"Done, written to {out_path}")
