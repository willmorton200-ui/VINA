import cv2
import numpy as np
import os
import json
import difflib

from pipeline.stage5_ocr import Stage5OCRDecoder
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage3_optimization import Stage3CylinderOptimizer
from pipeline.stage4_remapping import Stage4Remapper

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

ocr = Stage5OCRDecoder(use_gpu=True)
p1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()
optimizer = Stage3CylinderOptimizer(grid_rows=24, grid_cols=32)
remapper = Stage4Remapper(interpolation_mode="lanczos")

items_to_compare = [
    {
        "id": "white_main",
        "title": "Белая бутылка (Castillo de Liria Sauvignon Blanc)",
        "box": [479, 263, 960, 840],
        "crop": [460, 240, 960, 860],
        "ground_truth": "SINCE 1971 CASTILLO de LIRIA Medium Sweet THE INFLUENCE OF THE MEDITERRANEAN SEA ON THIS LAND IS ESSENTIAL FOR THE PRODUCTION OF HIGH-QUALITY WINES ESPECIALLY THOSE WHICH COMBINE YOUTH AND FRESHNESS"
    },
    {
        "id": "red_main",
        "title": "Красная бутылка (Castillo de Liria Monastrell)",
        "box": [0, 273, 463, 832],
        "crop": [0, 250, 470, 850],
        "ground_truth": "SINCE 1971 CASTILLO de LIRIA Medium Sweet THE INFLUENCE OF THE MEDITERRANEAN SEA ON THIS LAND IS ESSENTIAL FOR THE PRODUCTION OF HIGH-QUALITY WINES ESPECIALLY THOSE WHICH COMBINE ELEGANCE AND INTENSITY Cont. Net."
    },
    {
        "id": "red_lower",
        "title": "Нижняя этикетка красного вина (Monastrell)",
        "box": [144, 817, 448, 1020],
        "crop": [130, 800, 460, 1040],
        "ground_truth": "MONASTRELL VINO TINTO SEMI DULCE MEDIUM SWEET RED WINE"
    },
    {
        "id": "white_lower",
        "title": "Нижняя этикетка белого вина (Sauvignon Blanc)",
        "box": [501, 824, 814, 1025],
        "crop": [480, 800, 840, 1050],
        "ground_truth": "SAUVIGNON BLANC VIURA VINO BLANCO SEMI DULCE MEDIUM SWEET WHITE WINE"
    }
]

comparison_results = []

for item in items_to_compare:
    iid = item["id"]
    cx1, cy1, cx2, cy2 = item["crop"]
    crop_raw = img_bgr[cy1:cy2, cx1:cx2].copy()
    
    # 1. OCR on Raw 1x Crop
    res_raw = ocr.process(crop_raw)
    
    # 2. Dewarping v1.2
    mask_full, _ = p1.sam_refiner.refine_mask(img_bgr, item["box"])
    mask_crop = mask_full[cy1:cy2, cx1:cx2]
    vmask = vectorizer.vectorize(mask_crop)
    boundaries = {
        "P_TL": vmask.P_TL, "P_TR": vmask.P_TR,
        "P_BL": vmask.P_BL, "P_BR": vmask.P_BR,
        "T_curve_xs": vmask.T_curve[:, 0], "T_curve_ys": vmask.T_curve[:, 1],
        "B_curve_xs": vmask.B_curve[:, 0], "B_curve_ys": vmask.B_curve[:, 1],
        "L_curve": vmask.L_line, "R_curve": vmask.R_line
    }
    res_s3 = optimizer.process(crop_raw, [], [], {}, mask_crop, boundaries)
    res_s4 = remapper.process(crop_raw, res_s3)
    dewarped = res_s4["dewarped_bgr"]
    
    # 3. OCR on Dewarped Scan
    res_dewarped = ocr.process(dewarped)
    
    # Save visual comparison side by side
    h_vis = 480
    w_raw = int(crop_raw.shape[1] * (h_vis / float(crop_raw.shape[0])))
    w_dew = int(dewarped.shape[1] * (h_vis / float(dewarped.shape[0])))
    
    vis_raw = cv2.resize(res_raw["annotated_bgr"], (w_raw, h_vis), interpolation=cv2.INTER_LANCZOS4)
    vis_dew = cv2.resize(res_dewarped["annotated_bgr"], (w_dew, h_vis), interpolation=cv2.INTER_LANCZOS4)
    
    # Banners
    b1 = np.zeros((45, w_raw, 3), dtype=np.uint8) + 30
    cv2.putText(b1, f"БЕЗ трансформации (1x Кроп) - {len(res_raw['text_blocks'])} слов", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 165, 255), 2, cv2.LINE_AA)
    card1 = np.vstack((b1, vis_raw))
    
    b2 = np.zeros((45, w_dew, 3), dtype=np.uint8) + 30
    cv2.putText(b2, f"С трансформацией v1.2 (Dewarped) - {len(res_dewarped['text_blocks'])} слов", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 0), 2, cv2.LINE_AA)
    card2 = np.vstack((b2, vis_dew))
    
    pair = np.hstack((card1, card2))
    header = np.zeros((55, pair.shape[1], 3), dtype=np.uint8) + 15
    cv2.putText(header, f"Сравнение OCR: {item['title']}", (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    final_pair = np.vstack((header, pair))
    
    out_img_path = os.path.join(artifacts_dir, f"ocr_comparison_{iid}.png")
    cv2.imwrite(out_img_path, final_pair)
    print(f"Saved: {out_img_path}")
    
    comparison_results.append({
        "id": iid,
        "title": item["title"],
        "ground_truth": item["ground_truth"],
        "raw_ocr": {
            "num_words": len(res_raw["text_blocks"]),
            "full_text": res_raw["full_text"],
            "blocks": [{"text": b["text"], "conf": round(b.get("confidence", 0.0), 3)} for b in res_raw["text_blocks"]]
        },
        "dewarped_ocr": {
            "num_words": len(res_dewarped["text_blocks"]),
            "full_text": res_dewarped["full_text"],
            "blocks": [{"text": b["text"], "conf": round(b.get("confidence", 0.0), 3)} for b in res_dewarped["text_blocks"]]
        }
    })

with open(os.path.join(artifacts_dir, "ocr_raw_vs_dewarped_detailed.json"), "w", encoding="utf-8") as f:
    json.dump(comparison_results, f, ensure_ascii=False, indent=2)

print("\nDetailed OCR comparison generated successfully!")
