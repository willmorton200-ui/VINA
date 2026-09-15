"""
Test script for Version 1.2 algorithm:
- Step 1: Input image & dominant label detection
- Step 2: Mask segmentation & tight crop by mask dimensions
- Step 3: Lateral side vectors and 4 corner inflection points (P_TL, P_TR, P_BL, P_BR)
- Step 4: Top and bottom contrast transition boundary curves matching mask profiles
- Step 5: 3D deformation mesh with exact lateral vectors and top/bottom curves
- Step 6: Isometric dewarping/rectification and OCR text extraction
"""

import os
import cv2
import numpy as np
import json
import torch

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer, LabelShape, VectorMask
from pipeline.stage3_optimization import Stage3CylinderOptimizer
from pipeline.stage4_remapping import Stage4Remapper
from pipeline.stage5_ocr import Stage5OCRDecoder

def run_v12_test():
    artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
    os.makedirs(artifacts_dir, exist_ok=True)
    
    img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
    img_bgr = cv2.imread(img_path)
    h_img, w_img = img_bgr.shape[:2]
    
    print(f"Loaded image: {img_path} ({w_img}x{h_img})")
    
    # Initialize Stage 1 preprocessor
    p1 = Stage1Preprocessor(use_gpu=True)
    
    # We will test on both the White Bottle (Castillo de Liria Viura Sauvignon Blanc)
    # and the Red Bottle (Castillo de Liria Monastrell)
    bottles_to_test = [
        {
            "name": "castillo_white",
            "title": "Castillo de Liria (Viura Sauvignon Blanc - Белая)",
            "box": [479, 263, 960, 840],
            "crop_coords": [460, 240, 960, 860]
        },
        {
            "name": "castillo_red",
            "title": "Castillo de Liria (Monastrell Medium Sweet - Красная)",
            "box": [0, 273, 463, 832],
            "crop_coords": [0, 250, 470, 850]
        }
    ]
    
    remapper = Stage4Remapper()
    ocr = Stage5OCRDecoder(use_gpu=True)
    
    for b_info in bottles_to_test:
        b_name = b_info["name"]
        print(f"\n=======================================================")
        print(f" Processing: {b_info['title']}")
        print(f"=======================================================")
        
        bx1, by1, bx2, by2 = b_info["box"]
        bw = bx2 - bx1
        bh = by2 - by1
        
        # --- STEP 1: Original Image & ROI Crop ---
        cx1, cy1, cx2, cy2 = b_info["crop_coords"]
        crop_bgr = img_bgr[cy1:cy2, cx1:cx2].copy()
        ch, cw = crop_bgr.shape[:2]
        
        # --- STEP 2: SAM High-Precision Mask ---
        # Run SAM refinement on the bottle label box
        box_for_sam = [bx1, by1, bx2, by2]
        mask_full, _ = p1.sam_refiner.refine_mask(img_bgr, box_for_sam)
        mask_crop = mask_full[cy1:cy2, cx1:cx2]
        
        # Clean connected components
        binary = np.uint8(mask_crop > 127)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        if num_labels > 2:
            largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            clean_mask = np.zeros_like(mask_crop)
            clean_mask[labels == largest_label] = 255
            mask_crop = clean_mask
            
        # Tight crop by mask bounding dimensions
        y_indices, x_indices = np.where(mask_crop > 127)
        x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))
        y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
        
        # Tight mask and tight crop
        tight_crop_bgr = crop_bgr[y_min:y_max, x_min:x_max]
        tight_mask = mask_crop[y_min:y_max, x_min:x_max]
        
        # Visual: Step 2 - Mask and tight crop overlay
        vis_mask = crop_bgr.copy()
        mask_overlay = np.zeros_like(crop_bgr)
        mask_overlay[mask_crop > 127] = [0, 255, 0] # green mask
        vis_step2 = cv2.addWeighted(vis_mask, 0.70, mask_overlay, 0.30, 0)
        cv2.rectangle(vis_step2, (x_min, y_min), (x_max, y_max), (0, 255, 255), 2)
        
        # --- STEP 3 & 4: Lateral Side Vectors & Top/Bottom Contrast Curves ---
        vectorizer = MaskVectorizer()
        vmask = vectorizer.vectorize(mask_crop)
        
        P_TL = vmask.P_TL
        P_TR = vmask.P_TR
        P_BL = vmask.P_BL
        P_BR = vmask.P_BR
        T_curve = vmask.T_curve
        B_curve = vmask.B_curve
        L_line = vmask.L_line
        R_line = vmask.R_line
        
        print(f"  P_TL: {P_TL.round(1)}, P_TR: {P_TR.round(1)}")
        print(f"  P_BL: {P_BL.round(1)}, P_BR: {P_BR.round(1)}")
        
        # Visual: Step 3 - Lateral Vectors and Corner Points
        vis_step3 = crop_bgr.copy()
        # Draw lateral side vectors in bright blue
        cv2.line(vis_step3, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
        cv2.line(vis_step3, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)
        # Draw 4 corner points
        for pt, name in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
            cv2.circle(vis_step3, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(vis_step3, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.putText(vis_step3, name, (int(pt[0]) + 10, int(pt[1]) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
            
        # Visual: Step 4 - Boundary Curves matching mask contrast transition
        vis_step4 = vis_step3.copy()
        cv2.polylines(vis_step4, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
        cv2.polylines(vis_step4, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
        
        # --- STEP 5: 3D Deformation Mesh Construction ---
        optimizer = Stage3CylinderOptimizer(grid_rows=24, grid_cols=32)
        boundaries_dict = {
            "P_TL": P_TL, "P_TR": P_TR, "P_BL": P_BL, "P_BR": P_BR,
            "T_curve_xs": T_curve[:, 0], "T_curve_ys": T_curve[:, 1],
            "B_curve_xs": B_curve[:, 0], "B_curve_ys": B_curve[:, 1],
            "L_curve": L_line, "R_curve": R_line
        }
        res_s3 = optimizer.process(
            img_bgr=crop_bgr,
            text_lines=[],
            line_segments=[],
            cam_info={},
            mask=mask_crop,
            label_boundaries=boundaries_dict
        )
        
        vis_step5 = res_s3["vis_mesh"].copy()
        
        # --- STEP 6: Dewarping & Rectification + OCR ---
        res_s4 = remapper.process(crop_bgr, res_s3)
        dewarped_bgr = res_s4["dewarped_bgr"]
        
        # Run OCR on dewarped scan
        ocr_res = ocr.process(dewarped_bgr)
        annotated_bgr = ocr_res["annotated_bgr"]
        full_text = ocr_res["full_text"]
        print(f"  OCR extracted {ocr_res['num_words']} words: {full_text[:120]}...")
        
        # Save step artifacts for report
        cv2.imwrite(os.path.join(artifacts_dir, f"{b_name}_step1_crop.png"), crop_bgr)
        cv2.imwrite(os.path.join(artifacts_dir, f"{b_name}_step2_mask.png"), vis_step2)
        cv2.imwrite(os.path.join(artifacts_dir, f"{b_name}_step3_vectors.png"), vis_step3)
        cv2.imwrite(os.path.join(artifacts_dir, f"{b_name}_step4_curves.png"), vis_step4)
        cv2.imwrite(os.path.join(artifacts_dir, f"{b_name}_step5_3d_mesh.png"), vis_step5)
        cv2.imwrite(os.path.join(artifacts_dir, f"{b_name}_step6_dewarped.png"), dewarped_bgr)
        cv2.imwrite(os.path.join(artifacts_dir, f"{b_name}_step6_ocr.png"), annotated_bgr)
        
    print("\nAll step-by-step visualizations generated and saved to artifacts successfully!")

if __name__ == "__main__":
    run_v12_test()
