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

def run_tbilvino_pipeline():
    artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
    os.makedirs(artifacts_dir, exist_ok=True)
    
    img_path = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97\.user_uploaded\media_1787780608266.jpg"
    img_bgr = cv2.imread(img_path)
    h_img, w_img = img_bgr.shape[:2]
    print(f"Loaded Tbilvino image: {w_img}x{h_img}")
    
    p1 = Stage1Preprocessor(use_gpu=True)
    vectorizer = MaskVectorizer()
    optimizer = Stage3CylinderOptimizer(grid_rows=24, grid_cols=32)
    remapper = Stage4Remapper(interpolation_mode="lanczos")
    ocr = Stage5OCRDecoder(use_gpu=True)
    
    bottles = [
        {
            "id": "tbilvino_red",
            "name": "TBILVINO SACHINO (Красное полусухое / Red Medium Dry)",
            "box": [76, 263, 384, 881],
            "crop": [60, 240, 400, 900]
        },
        {
            "id": "tbilvino_white",
            "name": "TBILVINO SACHINO (Белое полусухое / White Medium Dry)",
            "box": [384, 264, 704, 920],
            "crop": [370, 240, 720, 930]
        }
    ]
    
    results = {}
    
    for b in bottles:
        bid = b["id"]
        cx1, cy1, cx2, cy2 = b["crop"]
        crop_bgr = img_bgr[cy1:cy2, cx1:cx2].copy()
        
        # 1. SAM Mask
        mask_full, _ = p1.sam_refiner.refine_mask(img_bgr, b["box"])
        mask_crop = mask_full[cy1:cy2, cx1:cx2]
        
        # Clean mask
        binary = np.uint8(mask_crop > 127)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        if num_labels > 2:
            largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            clean_mask = np.zeros_like(mask_crop)
            clean_mask[labels == largest_label] = 255
            mask_crop = clean_mask
            
        y_indices, x_indices = np.where(mask_crop > 127)
        x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))
        y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
        
        # Step 2: Mask overlay
        vis_mask = crop_bgr.copy()
        mask_overlay = np.zeros_like(crop_bgr)
        mask_overlay[mask_crop > 127] = [0, 255, 0]
        vis_step2 = cv2.addWeighted(vis_mask, 0.70, mask_overlay, 0.30, 0)
        cv2.rectangle(vis_step2, (x_min, y_min), (x_max, y_max), (0, 255, 255), 2)
        
        # Step 3 & 4: Exact Vectorization (v1.2)
        vmask = vectorizer.vectorize(mask_crop)
        P_TL, P_TR = vmask.P_TL, vmask.P_TR
        P_BL, P_BR = vmask.P_BL, vmask.P_BR
        T_curve, B_curve = vmask.T_curve, vmask.B_curve
        L_line, R_line = vmask.L_line, vmask.R_line
        
        print(f"\n[{b['name']}]")
        print(f"  P_TL: {P_TL.round(1)} | P_TR: {P_TR.round(1)}")
        print(f"  P_BL: {P_BL.round(1)} | P_BR: {P_BR.round(1)}")
        
        vis_step3 = crop_bgr.copy()
        cv2.line(vis_step3, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
        cv2.line(vis_step3, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)
        for pt, lbl in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
            px, py = int(pt[0]), int(pt[1])
            cv2.circle(vis_step3, (px, py), 8, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(vis_step3, (px, py), 6, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.putText(vis_step3, lbl, (px + 10, py - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
            
        vis_step4 = vis_step3.copy()
        cv2.polylines(vis_step4, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
        cv2.polylines(vis_step4, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
        
        # Step 5: 3D Grid
        boundaries = {
            "P_TL": P_TL, "P_TR": P_TR, "P_BL": P_BL, "P_BR": P_BR,
            "T_curve_xs": T_curve[:, 0], "T_curve_ys": T_curve[:, 1],
            "B_curve_xs": B_curve[:, 0], "B_curve_ys": B_curve[:, 1],
            "L_curve": L_line, "R_curve": R_line
        }
        res_s3 = optimizer.process(crop_bgr, [], [], {}, mask_crop, boundaries)
        vis_step5 = res_s3["vis_mesh"]
        
        # Step 6: Dewarping
        res_s4 = remapper.process(crop_bgr, res_s3)
        dewarped = res_s4["dewarped_bgr"]
        
        # OCR on Raw 1x Crop vs Dewarped Scan
        ocr_raw = ocr.process(crop_bgr)
        ocr_dewarped = ocr.process(dewarped)
        
        print(f"  Raw 1x OCR: {ocr_raw['full_text']}")
        print(f"  Dewarped OCR: {ocr_dewarped['full_text']}")
        
        # Save step artifacts
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_1_crop.png"), crop_bgr)
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_2_mask.png"), vis_step2)
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_3_vectors.png"), vis_step3)
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_4_curves.png"), vis_step4)
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_5_3d_mesh.png"), vis_step5)
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_6_dewarped.png"), dewarped)
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_7_ocr_annotated.png"), ocr_dewarped["annotated_bgr"])
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_7_ocr_raw.png"), ocr_raw["annotated_bgr"])
        
        # Build 6-step summary board
        steps = [
            ("1. Исходный кроп", crop_bgr),
            ("2. Маска SAM", vis_step2),
            ("3. Образующие и 4 угла", vis_step3),
            ("4. Верх/Низ кривые", vis_step4),
            ("5. 3D Сетка Coon's Patch", vis_step5),
            ("6. Развертка + OCR", ocr_dewarped["annotated_bgr"])
        ]
        target_h = 420
        row1_imgs, row2_imgs = [], []
        for i, (lbl, simg) in enumerate(steps):
            scale = target_h / float(simg.shape[0])
            new_w = int(simg.shape[1] * scale)
            r = cv2.resize(simg, (new_w, target_h), interpolation=cv2.INTER_LANCZOS4)
            banner = np.zeros((40, new_w, 3), dtype=np.uint8) + 30
            cv2.putText(banner, lbl, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 255), 2, cv2.LINE_AA)
            card = cv2.copyMakeBorder(np.vstack((banner, r)), 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=[70, 70, 70])
            if i < 3:
                row1_imgs.append(card)
            else:
                row2_imgs.append(card)
                
        r1 = np.hstack(row1_imgs)
        r2 = np.hstack(row2_imgs)
        max_w = max(r1.shape[1], r2.shape[1])
        if r1.shape[1] < max_w:
            r1 = cv2.copyMakeBorder(r1, 0, 0, 0, max_w - r1.shape[1], cv2.BORDER_CONSTANT, value=[30, 30, 30])
        if r2.shape[1] < max_w:
            r2 = cv2.copyMakeBorder(r2, 0, 0, 0, max_w - r2.shape[1], cv2.BORDER_CONSTANT, value=[30, 30, 30])
            
        board = np.vstack((r1, r2))
        hdr = np.zeros((55, max_w, 3), dtype=np.uint8) + 20
        cv2.putText(hdr, f"VINA v1.2 Pipeline: {b['name']}", (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2, cv2.LINE_AA)
        final_board = np.vstack((hdr, board))
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_pipeline_board.png"), final_board)
        
        # Build Raw vs Dewarped OCR comparison card
        h_comp = 480
        w_r = int(crop_bgr.shape[1] * (h_comp / float(crop_bgr.shape[0])))
        w_d = int(dewarped.shape[1] * (h_comp / float(dewarped.shape[0])))
        c_raw = cv2.resize(ocr_raw["annotated_bgr"], (w_r, h_comp), interpolation=cv2.INTER_LANCZOS4)
        c_dew = cv2.resize(ocr_dewarped["annotated_bgr"], (w_d, h_comp), interpolation=cv2.INTER_LANCZOS4)
        
        b_r = np.zeros((45, w_r, 3), dtype=np.uint8) + 30
        cv2.putText(b_r, f"1x Кроп (БЕЗ трансформации) - {len(ocr_raw['text_blocks'])} сл.", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 165, 255), 2, cv2.LINE_AA)
        
        b_d = np.zeros((45, w_d, 3), dtype=np.uint8) + 30
        cv2.putText(b_d, f"Развертка v1.2 (Dewarped) - {len(ocr_dewarped['text_blocks'])} сл.", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 255, 0), 2, cv2.LINE_AA)
        
        comp_pair = np.hstack((np.vstack((b_r, c_raw)), np.vstack((b_d, c_dew))))
        hdr_comp = np.zeros((55, comp_pair.shape[1], 3), dtype=np.uint8) + 15
        cv2.putText(hdr_comp, f"Сравнение OCR: {b['name']}", (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
        final_comp = np.vstack((hdr_comp, comp_pair))
        cv2.imwrite(os.path.join(artifacts_dir, f"{bid}_ocr_comparison.png"), final_comp)
        
        results[bid] = {
            "name": b["name"],
            "corners": {
                "P_TL": [round(v, 1) for v in P_TL.tolist()],
                "P_TR": [round(v, 1) for v in P_TR.tolist()],
                "P_BL": [round(v, 1) for v in P_BL.tolist()],
                "P_BR": [round(v, 1) for v in P_BR.tolist()]
            },
            "raw_text": ocr_raw["full_text"],
            "raw_words": len(ocr_raw["text_blocks"]),
            "dewarped_text": ocr_dewarped["full_text"],
            "dewarped_words": len(ocr_dewarped["text_blocks"]),
            "blocks": [{"text": b_item["text"], "conf": round(b_item.get("confidence", 0.0), 3)} for b_item in ocr_dewarped["text_blocks"]]
        }
        
    with open(os.path.join(artifacts_dir, "tbilvino_results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print("\nTbilvino test completed successfully!")

if __name__ == "__main__":
    run_tbilvino_pipeline()
