import cv2
import numpy as np
import os
import json
import easyocr

from pipeline.dewarp_engine import CylindricalDewarpEngine
from pipeline.vectorizer import MaskVectorizer

# Initialize engine
engine = CylindricalDewarpEngine(languages=['ru', 'en'], use_gpu=True)
reader = easyocr.Reader(['ru', 'en'], gpu=True)
vec = MaskVectorizer()

bottles = [
    {
        "id": "alma_valley",
        "title": "Бутылка 1: Alma Valley Cabernet Sauvignon Reserve",
        "path": r"test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"
    },
    {
        "id": "sarkel",
        "title": "Бутылка 2: Крепость Саркел Цимлянский Черный",
        "path": r"test_dataset/butilki/photo_2026-08-11_21-10-07.jpg"
    }
]

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
results_summary = []

for b_info in bottles:
    b_id = b_info["id"]
    img_bgr = cv2.imread(b_info["path"])
    print(f"\n=======================================================")
    print(f"Processing {b_info['title']}...")
    print(f"=======================================================")
    
    out_dir = rf"D:\VINA\outputs\report_2_bottles\{b_id}"
    os.makedirs(out_dir, exist_ok=True)
    
    res = engine.process_image(img_bgr, save_dir=out_dir)
    
    crop = cv2.imread(os.path.join(out_dir, "stage1_retinex.png"))
    mask = cv2.imread(os.path.join(out_dir, "stage1_mask.png"), cv2.IMREAD_GRAYSCALE)
    if len(mask.shape) == 3:
        mask = mask[:, :, 0]
        
    dewarp = cv2.imread(os.path.join(out_dir, "flattened_image.png"))
    mesh_vis = cv2.imread(os.path.join(out_dir, "stage3_mesh.png"))
    
    # Vectorize Mask
    vm = vec.vectorize(mask)
    P_TL = vm.P_TL
    P_TR = vm.P_TR
    P_BL = vm.P_BL
    P_BR = vm.P_BR
    
    # 1. Semitransparent Greenish Mask Overlay on Bottle
    vis_overlay = crop.copy()
    mask_2d = (mask > 127)
    
    # Create green overlay
    green_overlay = crop.copy()
    green_overlay[mask_2d] = [40, 225, 60]
    
    # Blend: 35% green tint + 65% original
    vis_overlay[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_overlay[mask_2d], 0.35, 0)
    
    # Blue side lines
    cv2.line(vis_overlay, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
    cv2.line(vis_overlay, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)
    
    # Green curves
    cv2.polylines(vis_overlay, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
    cv2.polylines(vis_overlay, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
    
    # Red central axis
    p_top_mid = (P_TL + P_TR) / 2.0
    p_bot_mid = (P_BL + P_BR) / 2.0
    for s in range(0, int(np.linalg.norm(p_bot_mid - p_top_mid)), 14):
        v_s = s / float(np.linalg.norm(p_bot_mid - p_top_mid))
        pt_a = (1.0 - v_s) * p_top_mid + v_s * p_bot_mid
        cv2.line(vis_overlay, (int(pt_a[0]), int(pt_a[1])), (int(pt_a[0]), int(pt_a[1] + 7)), (0, 0, 255), 2, cv2.LINE_AA)
        
    # 4 Corner Green Dots
    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)
        
    overlay_filename = f"{b_id}_report_greenish_overlay.png"
    cv2.imwrite(os.path.join(artifacts_dir, overlay_filename), vis_overlay)
    
    # 2. 3D Mesh Visualization
    mesh_filename = f"{b_id}_report_3d_mesh.png"
    cv2.imwrite(os.path.join(artifacts_dir, mesh_filename), mesh_vis)
    
    # 3. Flattened Dewarped Label
    dewarp_filename = f"{b_id}_report_dewarped.png"
    cv2.imwrite(os.path.join(artifacts_dir, dewarp_filename), dewarp)
    
    # 4. Detailed OCR Recognition
    ocr_res = reader.readtext(dewarp)
    vis_ocr = dewarp.copy()
    ocr_tokens = []
    ocr_res.sort(key=lambda r: min(p[1] for p in r[0]))
    
    for idx, (bbox, text, conf) in enumerate(ocr_res, start=1):
        pts = np.array(bbox, dtype=np.int32)
        x_min, y_min = np.min(pts, axis=0)
        x_max, y_max = np.max(pts, axis=0)
        clean_text = text.strip()
        if clean_text:
            ocr_tokens.append({
                "id": idx,
                "text": clean_text,
                "confidence": round(float(conf) * 100.0, 1)
            })
            cv2.polylines(vis_ocr, [pts], isClosed=True, color=(0, 255, 0), thickness=2, lineType=cv2.LINE_AA)
            label_str = f"{clean_text} ({conf*100.0:.0f}%)"
            (t_w, t_h), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            tag_y = max(y_min - 4, t_h + 4)
            cv2.rectangle(vis_ocr, (x_min, tag_y - t_h - 2), (x_min + t_w + 6, tag_y + 2), (0, 0, 0), -1)
            cv2.putText(vis_ocr, label_str, (x_min + 3, tag_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

    ocr_filename = f"{b_id}_report_ocr_annotated.png"
    cv2.imwrite(os.path.join(artifacts_dir, ocr_filename), vis_ocr)
    
    results_summary.append({
        "id": b_id,
        "title": b_info["title"],
        "overlay_img": overlay_filename,
        "mesh_img": mesh_filename,
        "dewarp_img": dewarp_filename,
        "ocr_img": ocr_filename,
        "corners": {
            "P_TL": [round(float(P_TL[0]), 1), round(float(P_TL[1]), 1)],
            "P_TR": [round(float(P_TR[0]), 1), round(float(P_TR[1]), 1)],
            "P_BL": [round(float(P_BL[0]), 1), round(float(P_BL[1]), 1)],
            "P_BR": [round(float(P_BR[0]), 1), round(float(P_BR[1]), 1)]
        },
        "ocr_tokens": ocr_tokens,
        "total_ms": round(res["timings"]["total_ms"], 1)
    })

# Save JSON
with open(os.path.join(artifacts_dir, "two_bottles_summary.json"), "w", encoding="utf-8") as f:
    json.dump(results_summary, f, ensure_ascii=False, indent=2)

print("\nBatch processing of 2 bottles complete successfully!")
