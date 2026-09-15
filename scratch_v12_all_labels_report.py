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

def run_all_labels_report():
    artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
    img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-29.jpg')
    
    p1 = Stage1Preprocessor(use_gpu=True)
    vectorizer = MaskVectorizer()
    optimizer = Stage3CylinderOptimizer(grid_rows=24, grid_cols=32)
    remapper = Stage4Remapper(interpolation_mode="lanczos")
    ocr = Stage5OCRDecoder(use_gpu=True)
    
    sublabels = [
        {
            "id": "white_lower",
            "name": "Нижняя контрэтикетка белого вина (Sauvignon Blanc Viura)",
            "box": [501, 824, 814, 1025],
            "crop": [480, 800, 840, 1050]
        },
        {
            "id": "red_lower",
            "name": "Нижняя контрэтикетка красного вина (Monastrell)",
            "box": [144, 817, 448, 1020],
            "crop": [130, 800, 460, 1040]
        }
    ]
    
    for sub in sublabels:
        sid = sub["id"]
        cx1, cy1, cx2, cy2 = sub["crop"]
        crop_bgr = img[cy1:cy2, cx1:cx2].copy()
        
        mask_full, _ = p1.sam_refiner.refine_mask(img, sub["box"])
        mask_crop = mask_full[cy1:cy2, cx1:cx2]
        
        vmask = vectorizer.vectorize(mask_crop)
        boundaries_dict = {
            "P_TL": vmask.P_TL, "P_TR": vmask.P_TR,
            "P_BL": vmask.P_BL, "P_BR": vmask.P_BR,
            "T_curve_xs": vmask.T_curve[:, 0], "T_curve_ys": vmask.T_curve[:, 1],
            "B_curve_xs": vmask.B_curve[:, 0], "B_curve_ys": vmask.B_curve[:, 1],
            "L_curve": vmask.L_line, "R_curve": vmask.R_line
        }
        res_s3 = optimizer.process(crop_bgr, [], [], {}, mask_crop, boundaries_dict)
        res_s4 = remapper.process(crop_bgr, res_s3)
        dewarped = res_s4["dewarped_bgr"]
        ocr_res = ocr.process(dewarped)
        
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{sid}_crop.png"), crop_bgr)
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{sid}_mesh.png"), res_s3["vis_mesh"])
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{sid}_dewarped.png"), dewarped)
        cv2.imwrite(os.path.join(artifacts_dir, f"report_{sid}_ocr.png"), ocr_res["annotated_bgr"])
        print(f"[{sub['name']}] OCR: {ocr_res['full_text']}")

run_all_labels_report()
