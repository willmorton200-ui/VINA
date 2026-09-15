import os
import cv2
import numpy as np
import json
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

def run_report():
    dataset_dir = "d:/VINA/test_dataset/butilki"
    brain_dir = "C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97"
    out_dir = os.path.join(brain_dir, "segmentation_report_20")
    os.makedirs(out_dir, exist_ok=True)
    
    files = [f for f in os.listdir(dataset_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(dataset_dir, f)), reverse=True)
    target_files = files[:20]
    
    stage1 = Stage1Preprocessor(use_gpu=True)
    vectorizer = MaskVectorizer()
    
    report_items = []
    
    print(f"Starting segmentation & guide evaluation for 20 images...")
    for idx, fname in enumerate(target_files):
        fpath = os.path.join(dataset_dir, fname)
        img_bgr = cv2.imread(fpath)
        if img_bgr is None:
            continue
            
        h_orig, w_orig = img_bgr.shape[:2]
        
        # 1. Run Stage 1 segmentation & tight crop
        cropped_bgr, cropped_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)
        
        # 2. Extract guides and corners
        vec = vectorizer.vectorize(cropped_mask)
        
        # 3. Create visual guide overlay on crop
        vis_features = cropped_bgr.copy()
        cv2.polylines(vis_features, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
        for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
            cv2.circle(vis_features, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.circle(vis_features, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 2, cv2.LINE_AA)
            
        # 4. Create original image with localized label bbox
        vis_orig = img_bgr.copy()
        crop_x = bbox_info.get("crop_x", 0)
        crop_y = bbox_info.get("crop_y", 0)
        crop_w = bbox_info.get("crop_w", w_orig)
        crop_h = bbox_info.get("crop_h", h_orig)
        cv2.rectangle(vis_orig, (crop_x, crop_y), (crop_x + crop_w, crop_y + crop_h), (0, 255, 255), 4)
        
        # 5. Convert mask to 3-channel for side-by-side assembly
        vis_mask = cv2.cvtColor(cropped_mask, cv2.COLOR_GRAY2BGR)
        
        # Standardize heights for neat side-by-side board
        board_h = 450
        def resize_to_h(im, th):
            ih, iw = im.shape[:2]
            tw = max(int(round(iw * (th / float(ih)))), 50)
            return cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA)
            
        p1 = resize_to_h(vis_orig, board_h)
        p2 = resize_to_h(vis_mask, board_h)
        p3 = resize_to_h(vis_features, board_h)
        
        # Add labels on top of each panel
        def add_header(im, text):
            canvas = np.zeros((im.shape[0] + 40, im.shape[1], 3), dtype=np.uint8)
            canvas[40:, :] = im
            cv2.putText(canvas, text, (10, 28), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 1, cv2.LINE_AA)
            return canvas
            
        p1_h = add_header(p1, "1. Iskhodnik (YOLO)")
        p2_h = add_header(p2, "2. Krop Maski (10px pad)")
        p3_h = add_header(p3, "3. Napravlyayushchie")
        
        # Stack horizontally with vertical dividers
        divider = np.full((board_h + 40, 4, 3), 120, dtype=np.uint8)
        board = np.hstack((p1_h, divider, p2_h, divider, p3_h))
        
        # Save board image
        safe_name = f"sample_{idx+1:02d}_{fname.replace(' ', '_').replace('(', '').replace(')', '')}.png"
        board_path = os.path.join(out_dir, safe_name)
        cv2.imwrite(board_path, board)
        
        # Calculate stats
        mask_area = int(np.count_nonzero(cropped_mask))
        w_c, h_c = cropped_bgr.shape[1], cropped_bgr.shape[0]
        
        report_items.append({
            "idx": idx + 1,
            "filename": fname,
            "board_path": board_path,
            "board_filename": safe_name,
            "orig_size": f"{w_orig}x{h_orig}",
            "crop_size": f"{w_c}x{h_c}",
            "mask_area": mask_area,
            "P_TL": [round(float(v), 1) for v in vec.P_TL],
            "P_TR": [round(float(v), 1) for v in vec.P_TR],
            "P_BL": [round(float(v), 1) for v in vec.P_BL],
            "P_BR": [round(float(v), 1) for v in vec.P_BR]
        })
        print(f"[{idx+1:02d}/20] Processed {fname} -> {safe_name}")

    # Write JSON results
    json_path = os.path.join(brain_dir, "segmentation_20_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_items, f, ensure_ascii=False, indent=2)

    # Generate Markdown Report Artifact
    md_path = os.path.join(brain_dir, "segmentation_20_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 📋 Отчет по сегментации последних 20 картинок\n\n")
        f.write("В отчете представлены 3 стадии для каждой из 20 последних бутылок:\n")
        f.write("1. **Исходник** с рамкой локализации главной этикетки.\n")
        f.write("2. **Кроп маски** (сглаженный монолитный контур с гарантированным запасом 10 px без среза краев).\n")
        f.write("3. **Направляющие** (боковые образующие $L, R$, верхняя/нижняя дуги $T, B$ и 4 угла $P_{TL}, P_{TR}, P_{BL}, P_{BR}$).\n\n")
        f.write("---\n\n")
        
        for item in report_items:
            f.write(f"### Образец №{item['idx']:02d}: `{item['filename']}`\n\n")
            f.write(f"- **Разрешение исходника:** `{item['orig_size']}`\n")
            f.write(f"- **Размер кропа (с запасом 10px):** `{item['crop_size']}` (площадь маски: `{item['mask_area']:,} px`)\n")
            f.write(f"- **Углы:** $P_{{TL}}$: `{item['P_TL']}`, $P_{{TR}}$: `{item['P_TR']}`, $P_{{BL}}$: `{item['P_BL']}`, $P_{{BR}}$: `{item['P_BR']}`\n\n")
            f.write(f"![{item['filename']}](/C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/segmentation_report_20/{item['board_filename']})\n\n")
            f.write("---\n\n")
            
    print(f"\nReport successfully generated at: {md_path}")

if __name__ == "__main__":
    run_report()
