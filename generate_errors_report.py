import os
import cv2
import time
import base64
import numpy as np

from pipeline.catalog import WineCatalog
from pipeline.search_engine import WineSearchEngine
from pipeline.vina_studio_matcher import VinaStudioMatcher
from pipeline.dewarp_engine import CylindricalDewarpEngine
from pipeline.color_matcher import calculate_visual_color_bonus

print("Loading models...")
catalog = WineCatalog(r"D:\VINA\wines_integrated_clean.csv")
search_engine = WineSearchEngine(catalog, r"D:\VINA\models\siglip2_index.faiss")
vina_matcher = VinaStudioMatcher(catalog)
engine = CylindricalDewarpEngine(use_gpu=True)

images = [
    "2039dd8a.jpg", "e3f116c0.jpeg", "10967716.jpg", 
    "4ea254fd.jpg", "f212df5b.jpeg", "35f764ae.jpg"
]
base_dir = r"D:\VINA\owner_eval\1\queries"

report_md = "# Отчет по ошибочным этикеткам (Цветовой бонус отключен)\n\n"

def b64_to_img(b64_str):
    if not b64_str: return None
    if "," in b64_str:
        b64_str = b64_str.split(",")[1]
    b = base64.b64decode(b64_str)
    n = np.frombuffer(b, np.uint8)
    return cv2.imdecode(n, cv2.IMREAD_COLOR)

for img_name in images:
    img_path = os.path.join(base_dir, img_name)
    report_md += f"## Файл: {img_name}\n\n"
    
    if not os.path.exists(img_path):
        report_md += f"**Ошибка**: Файл не найден.\n\n---\n\n"
        continue
        
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        report_md += f"**Ошибка**: Не удалось прочитать изображение.\n\n---\n\n"
        continue
        
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
    
    report_md += f"### Распознанный текст (OCR)\n"
    report_md += f"`	ext\n{ocr_text.strip() if ocr_text.strip() else '<текст не найден>'}\n`\n\n"
    
    report_md += "### Оценка Топ-5 кандидатов\n\n"
    
    # Re-sort
    candidates = sorted(candidates, key=lambda x: x["raw_final_confidence"] if "raw_final_confidence" in x else x["final_confidence"], reverse=True)
    
    if candidates:
        best = candidates[0]
        report_md += f"**Победитель:** {best['slug']} ({best['name']})\n"
        report_md += f"**Финальная Уверенность:** {best['final_confidence']:.2f}%\n\n"
        
        for i, c in enumerate(candidates):
            report_md += f"{i+1}. **[{c['name']}]** {c['slug']}\n"
            report_md += f"   - Embedding: {c.get('confidence_embedding', 0.0):.2f}\n"
            report_md += f"   - OCR Бонус: +{c.get('ocr_bonus', 0.0):.2f} (Совпадений слов: {c.get('match_count', 0)})\n"
            report_md += f"   - **Итого**: {c['final_confidence']:.2f}%\n\n"
    else:
        report_md += "Кандидаты не найдены.\n\n"
        
    report_md += "---\n\n"
    
output_file = r"C:\Users\User\.gemini\antigravity-ide\brain\7b04bd8a-c0c6-4939-afcb-f97f081bee38\cascade_errors_report.md"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(report_md)
print(f"Report written to {output_file}")
