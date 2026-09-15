import os
import cv2
import numpy as np
import json
import torch

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage3_optimization import Stage3CylinderOptimizer
from pipeline.stage4_remapping import Stage4Remapper
from pipeline.stage5_ocr import Stage5OCRDecoder

def run_comprehensive_report():
    artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
    os.makedirs(artifacts_dir, exist_ok=True)
    
    img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
    img_bgr = cv2.imread(img_path)
    
    p1 = Stage1Preprocessor(use_gpu=True)
    vectorizer = MaskVectorizer()
    optimizer = Stage3CylinderOptimizer(grid_rows=24, grid_cols=32)
    remapper = Stage4Remapper(interpolation_mode="lanczos")
    ocr = Stage5OCRDecoder(use_gpu=True)
    
    bottles = [
        {
            "id": "white",
            "name": "Castillo de Liria (Sauvignon Blanc & Viura)",
            "type": "Белое полусладкое (White Medium Sweet)",
            "box": [479, 263, 960, 840],
            "crop": [460, 240, 960, 860]
        },
        {
            "id": "red",
            "name": "Castillo de Liria (Monastrell)",
            "type": "Красное полусладкое (Red Medium Sweet)",
            "box": [0, 273, 463, 832],
            "crop": [0, 250, 470, 850]
        }
    ]
    
    results = {}
    
    for b in bottles:
        b_id = b["id"]
        cx1, cy1, cx2, cy2 = b["crop"]
        crop_bgr = img_bgr[cy1:cy2, cx1:cx2].copy()
        
        # 1. SAM Mask
        mask_full, _ = p1.sam_refiner.refine_mask(img_bgr, b["box"])
        mask_crop = mask_full[cy1:cy2, cx1:cx2]
        
        # 2. Exact Vectorization
        vmask = vectorizer.vectorize(mask_crop)
        
        # 3. 3D Deformation Grid
        boundaries_dict = {
            "P_TL": vmask.P_TL, "P_TR": vmask.P_TR,
            "P_BL": vmask.P_BL, "P_BR": vmask.P_BR,
            "T_curve_xs": vmask.T_curve[:, 0], "T_curve_ys": vmask.T_curve[:, 1],
            "B_curve_xs": vmask.B_curve[:, 0], "B_curve_ys": vmask.B_curve[:, 1],
            "L_curve": vmask.L_line, "R_curve": vmask.R_line
        }
        res_s3 = optimizer.process(crop_bgr, [], [], {}, mask_crop, boundaries_dict)
        vis_mesh = res_s3["vis_mesh"]
        
        # 4. Dewarping (Rectification)
        res_s4 = remapper.process(crop_bgr, res_s3)
        dewarped_bgr = res_s4["dewarped_bgr"]
        
        # 5. Raw OCR (on curved crop) vs Dewarped OCR (on rectified flat scan)
        ocr_raw = ocr.process(crop_bgr)
        ocr_dewarped = ocr.process(dewarped_bgr)
        
        # Save individual images
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{b_id}_1_crop.png"), crop_bgr)
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{b_id}_2_mesh.png"), vis_mesh)
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{b_id}_3_dewarped.png"), dewarped_bgr)
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{b_id}_4_ocr_annotated.png"), ocr_dewarped["annotated_bgr"])
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{b_id}_4_ocr_raw.png"), ocr_raw["annotated_bgr"])
        
        # Create Side-by-Side Comparison Card (Mesh -> Dewarped -> OCR)
        h_target = 480
        def resize_h(im, target_h):
            scale = target_h / float(im.shape[0])
            return cv2.resize(im, (int(im.shape[1] * scale), target_h), interpolation=cv2.INTER_LANCZOS4)
            
        card_mesh = resize_h(vis_mesh, h_target)
        card_dewarp = resize_h(dewarped_bgr, h_target)
        card_ocr = resize_h(ocr_dewarped["annotated_bgr"], h_target)
        
        # Add labels to cards
        def add_banner(im, txt, color):
            b = np.zeros((40, im.shape[1], 3), dtype=np.uint8) + 25
            cv2.putText(b, txt, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
            return np.vstack((b, im))
            
        c1 = add_banner(card_mesh, "1. 3D Сетка по контуру", (0, 255, 255))
        c2 = add_banner(card_dewarp, "2. Плоская развертка", (0, 255, 0))
        c3 = add_banner(card_ocr, "3. OCR Распознавание", (255, 180, 0))
        
        trio = np.hstack((c1, c2, c3))
        header = np.zeros((55, trio.shape[1], 3), dtype=np.uint8) + 15
        cv2.putText(header, f"VINA v1.2: {b['name']} ({b['type']})", (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        full_card = np.vstack((header, trio))
        
        card_path = os.path.join(artifacts_dir, f"report_{b_id}_full_trio.png")
        cv2.imwrite(card_path, full_card)
        print(f"Saved: {card_path}")
        
        results[b_id] = {
            "name": b["name"],
            "type": b["type"],
            "corners": {
                "P_TL": [round(x, 1) for x in vmask.P_TL.tolist()],
                "P_TR": [round(x, 1) for x in vmask.P_TR.tolist()],
                "P_BL": [round(x, 1) for x in vmask.P_BL.tolist()],
                "P_BR": [round(x, 1) for x in vmask.P_BR.tolist()]
            },
            "dewarped_size": [dewarped_bgr.shape[1], dewarped_bgr.shape[0]],
            "raw_ocr_words": len(ocr_raw["text_blocks"]),
            "raw_text": ocr_raw["full_text"],
            "dewarped_ocr_words": len(ocr_dewarped["text_blocks"]),
            "dewarped_text": ocr_dewarped["full_text"],
            "text_blocks": [
                {"text": tb["text"], "confidence": round(tb.get("confidence", 0.0), 3)}
                for tb in ocr_dewarped["text_blocks"]
            ]
        }
        
    with open(os.path.join(artifacts_dir, "v12_report_data.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("Comprehensive report processing complete!")

if __name__ == "__main__":
    run_comprehensive_report()
