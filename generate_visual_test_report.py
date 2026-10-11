import os
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from pipeline.dewarp_engine import CylindricalDewarpEngine

def draw_visual_report():
    output_dir = Path(r"C:\Users\User\.gemini\antigravity-ide\brain\f0053c95-5cec-49a8-aa09-dd98fd896a15")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    engine = CylindricalDewarpEngine()
    
    test_cases = [
        ("3c11e5b0.jpeg", "Многокомпонентный снимок: 3 наклейки на бутылке"),
        ("26ddb066.jpg", "Две наклейки: основная + вспомогательная"),
        ("04f3ce15.jpg", "Одиночная центральная наклейка на бутылке"),
        ("2039dd8a.jpg", "Сложный фон / две этикетки"),
    ]
    
    results_summary = []
    
    for filename, desc in test_cases:
        img_path = Path(r"d:\VINA\owner_eval\1\queries") / filename
        if not img_path.exists():
            continue
            
        img = cv2.imread(str(img_path))
        h, w = img.shape[:2]
        
        # Инференс через весь пайплайн
        res = engine.process_image(img)
        cropped_bgr, cropped_mask, bbox_info = engine.stage1.segment_bottle_and_label(img)
        
        # 1. Визуализируем детекцию на исходном фото
        vis_det = img.copy()
        
        # Бутылка (голубая рамка)
        bot_box = bbox_info.get("dominant_bottle_bbox")
        if bot_box:
            bx1, by1, bx2, by2 = bot_box
            cv2.rectangle(vis_det, (bx1, by1), (bx2, by2), (255, 180, 0), 4)
            cv2.putText(vis_det, "SELECTED BOTTLE", (bx1, max(30, by1 - 10)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 180, 0), 2)
                        
        # Наклейки
        bottle_labels = bbox_info.get("bottle_labels", [])
        for i, lbl in enumerate(bottle_labels):
            lx1, ly1, lx2, ly2 = lbl["box"]
            is_prim = lbl.get("is_primary", False)
            color = (0, 255, 0) if is_prim else (0, 165, 255) # Зеленый = Главная, Оранжевый = Доп.
            tag = f"PRIMARY LABEL #{i+1} ({lbl['conf']:.2f})" if is_prim else f"SECONDARY #{i+1} ({lbl['conf']:.2f})"
            cv2.rectangle(vis_det, (lx1, ly1), (lx2, ly2), color, 3)
            cv2.putText(vis_det, tag, (lx1, max(25, ly1 - 8)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                        
        # 2. Выпрямленный результат главной наклейки
        dewarped = res.get("dewarped")
        ocr_text = res.get("full_text", "")
        
        # Сохраняем исходную разметку и выпрямленную
        out_det_name = f"test_{filename}_detection.jpg"
        out_dew_name = f"test_{filename}_dewarped.jpg"
        
        # Ресайзим для красивого отображения в отчете
        max_h = 750
        scale = max_h / float(h) if h > max_h else 1.0
        vis_det_resized = cv2.resize(vis_det, (int(w * scale), int(h * scale)))
        
        cv2.imwrite(str(output_dir / out_det_name), vis_det_resized)
        if dewarped is not None and dewarped.size > 0:
            dh, dw = dewarped.shape[:2]
            d_scale = 450 / float(dh) if dh > 450 else 1.0
            dew_resized = cv2.resize(dewarped, (int(dw * d_scale), int(dh * d_scale)))
            cv2.imwrite(str(output_dir / out_dew_name), dew_resized)
            
        results_summary.append({
            "filename": filename,
            "desc": desc,
            "labels_count": len(bottle_labels),
            "bottle_found": bool(bot_box),
            "ocr_sample": ocr_text[:120] + "..." if len(ocr_text) > 120 else ocr_text,
            "img_det": out_det_name,
            "img_dew": out_dew_name
        })
        print(f"Processed {filename}: labels={len(bottle_labels)}, OCR len={len(ocr_text)}")
        
    print("All test images processed.")

if __name__ == "__main__":
    draw_visual_report()
