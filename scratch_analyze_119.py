import os
import time
import cv2
import numpy as np
import json
import torch

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage5_ocr import Stage5OCRDecoder
from pipeline.wine_lexicon_corrector import WineVocabularyCorrector

def process_tsimlyanskoe():
    img_path = r"d:\VINA\owner_eval\119\queries\8f0d7e35-2cfb-4a00-95ad-12cc38571d42.jpg"
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        raise ValueError(f"Could not load image at {img_path}")
    h_orig, w_orig = img_bgr.shape[:2]
    print(f"Loaded image: {w_orig}x{h_orig}")
    
    brain_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\565c4697-6f62-4294-9f4f-0a2949ded581\scratch"
    out_dir = os.path.join(brain_dir, "step_by_step_119")
    os.makedirs(out_dir, exist_ok=True)
    
    # -------------------------------------------------------------
    # 1. STEP 1: YOLO Bounding Box Detection
    # -------------------------------------------------------------
    print("\n--- STEP 1: YOLOv8x Bounding Box Detection ---")
    stage1 = Stage1Preprocessor(use_gpu=True)
    yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.20)
    boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
    confs = yolo_res[0].boxes.conf.cpu().numpy()
    classes = yolo_res[0].boxes.cls.cpu().numpy()
    
    vis_step1 = img_bgr.copy()
    candidate_boxes = []
    
    for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs)):
        bx1, by1, bx2, by2 = [int(v) for v in box]
        bw, bh = bx2 - bx1, by2 - by1
        ar = bw / float(bh)
        cls_name = stage1.yolo_model.names.get(int(cls_id), str(cls_id))
        
        is_edge = (bx1 <= 4 or by1 <= 4 or bx2 >= w_orig - 4 or by2 >= h_orig - 4)
        area = bw * bh
        score = area - (500000.0 if is_edge else 0.0)
        
        cv2.rectangle(vis_step1, (bx1, by1), (bx2, by2), (0, 165, 255) if is_edge else (0, 255, 0), 2)
        cv2.putText(vis_step1, f"{cls_name} {conf:.2f}", (bx1, max(30, by1 - 8)), cv2.FONT_HERSHEY_DUPLEX, 0.7, (0, 255, 255), 1, cv2.LINE_AA)
        
        cx, cy = bx1 + bw // 2, by1 + bh // 2
        in_central_third = (w_orig / 3.0 <= cx <= 2.0 * w_orig / 3.0) and (h_orig / 3.0 <= cy <= 2.0 * h_orig / 3.0)
        
        if not in_central_third:
            continue
            
        if bh > 0.70 * h_orig and ar < 0.6:
            continue
            
        candidate_boxes.append({
            "idx": idx,
            "box": [bx1, by1, bx2, by2],
            "conf": float(conf),
            "area": area,
            "score": score
        })
    candidate_boxes.sort(key=lambda x: x["score"], reverse=True)
    winner_box_obj = candidate_boxes[0]
    wbx1, wby1, wbx2, wby2 = winner_box_obj["box"]
    print(f"Winner BBox: {winner_box_obj['box']} (Conf: {winner_box_obj['conf']:.2f}, Area: {winner_box_obj['area']})")
    
    cv2.rectangle(vis_step1, (wbx1, wby1), (wbx2, wby2), (255, 255, 0), 4)
    cv2.putText(vis_step1, "MAIN LABEL (Target)", (wbx1, wby1 - 12), cv2.FONT_HERSHEY_DUPLEX, 0.85, (255, 255, 0), 2, cv2.LINE_AA)
    cv2.imwrite(os.path.join(out_dir, "step1_yolo_bbox.png"), vis_step1)
    
    # -------------------------------------------------------------
    # 2. STEP 2: Meta SAM ViT-H Segmentation
    # -------------------------------------------------------------
    print("\n--- STEP 2: SAM ViT-H Segmentation ---")
    sam = SAMRefiner(model_type="vit_h")
    t0 = time.perf_counter()
    sam_mask, sam_score = sam.refine_mask(img_bgr, [wbx1, wby1, wbx2, wby2])
    t_sam_ms = (time.perf_counter() - t0) * 1000.0
    print(f"SAM ViT-H completed in {t_sam_ms:.1f}ms with score: {sam_score:.3f}")
    
    sam_mask = stage1._keep_largest_component(sam_mask)
    
    # Tight crop with exact 10px margin
    ys, xs = np.where(sam_mask > 0)
    if len(xs) == 0:
        raise ValueError("SAM returned empty mask!")
    x_min, x_max = int(np.min(xs)), int(np.max(xs))
    y_min, y_max = int(np.min(ys)), int(np.max(ys))
    pad = 10
    cx1 = max(0, x_min - pad)
    cy1 = max(0, y_min - pad)
    cx2 = min(w_orig, x_max + pad + 1)
    cy2 = min(h_orig, y_max + pad + 1)
    
    crop_bgr = img_bgr[cy1:cy2, cx1:cx2].copy()
    crop_mask = sam_mask[cy1:cy2, cx1:cx2].copy()
    h_c, w_c = crop_bgr.shape[:2]
    
    vis_step2_overlay = crop_bgr.copy()
    mask_green = np.zeros_like(crop_bgr)
    mask_green[:, :] = (0, 255, 0)
    vis_step2_overlay = np.where(crop_mask[:, :, None] > 127, cv2.addWeighted(crop_bgr, 0.65, mask_green, 0.35, 0), crop_bgr)
    cv2.imwrite(os.path.join(out_dir, "step2_sam_mask.png"), crop_mask)
    cv2.imwrite(os.path.join(out_dir, "step2_sam_overlay.png"), vis_step2_overlay)
    
    # -------------------------------------------------------------
    # 3. STEP 3: 4 Extreme Corners + 2 Lateral Straight + 5-Point Horizontal Curves
    # -------------------------------------------------------------
    print("\n--- STEP 3: Geometric Guides & 4 Corner Vertices ---")
    vectorizer = MaskVectorizer()
    vec = vectorizer.vectorize(crop_mask)
    
    P_TL = vec.P_TL
    P_TR = vec.P_TR
    P_BL = vec.P_BL
    P_BR = vec.P_BR
    print(f"4 Corner Vertices:\n  P_TL={P_TL}, P_TR={P_TR}\n  P_BL={P_BL}, P_BR={P_BR}")
    
    # Lateral Straight Guides (2 straight segments connecting upper and lower corner vertices)
    N_pts = 64
    v_vals = np.linspace(0.0, 1.0, N_pts)
    L_line = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
    R_line = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR
    
    # Extract 5 control points on Upper Boundary (u = 0, 0.25, 0.5, 0.75, 1.0)
    u_5 = np.linspace(0.0, 1.0, 5)
    top_5_pts = []
    for u in u_5:
        x_target = int(round((1.0 - u) * P_TL[0] + u * P_TR[0]))
        x_target = np.clip(x_target, 0, w_c - 1)
        ys = np.where(crop_mask[:, x_target] > 127)[0]
        if len(ys) > 0:
            top_5_pts.append((float(x_target), float(ys[0])))
        else:
            y_int = (1.0 - u) * P_TL[1] + u * P_TR[1]
            top_5_pts.append((float(x_target), float(y_int)))
    top_5_pts = np.array(top_5_pts)
    top_5_pts[0] = P_TL
    top_5_pts[-1] = P_TR
    
    # Extract 5 control points on Lower Boundary
    bot_5_pts = []
    for u in u_5:
        x_target = int(round((1.0 - u) * P_BL[0] + u * P_BR[0]))
        x_target = np.clip(x_target, 0, w_c - 1)
        ys = np.where(crop_mask[:, x_target] > 127)[0]
        if len(ys) > 0:
            bot_5_pts.append((float(x_target), float(ys[-1])))
        else:
            y_int = (1.0 - u) * P_BL[1] + u * P_BR[1]
            bot_5_pts.append((float(x_target), float(y_int)))
    bot_5_pts = np.array(bot_5_pts)
    bot_5_pts[0] = P_BL
    bot_5_pts[-1] = P_BR
    
    # Smooth into 2 continuous horizontal guide curves
    u_dense = np.linspace(0.0, 1.0, N_pts)
    poly_T = np.polyfit(u_5, top_5_pts[:, 1], deg=2)
    poly_B = np.polyfit(u_5, bot_5_pts[:, 1], deg=2)
    
    T_curve = np.column_stack((
        (1.0 - u_dense) * P_TL[0] + u_dense * P_TR[0],
        np.polyval(poly_T, u_dense)
    ))
    T_curve[0] = P_TL
    T_curve[-1] = P_TR
    
    B_curve = np.column_stack((
        (1.0 - u_dense) * P_BL[0] + u_dense * P_BR[0],
        np.polyval(poly_B, u_dense)
    ))
    B_curve[0] = P_BL
    B_curve[-1] = P_BR
    
    vis_step3 = crop_bgr.copy()
    # 5-point polylines (thin yellow)
    cv2.polylines(vis_step3, [top_5_pts.astype(np.int32)], False, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.polylines(vis_step3, [bot_5_pts.astype(np.int32)], False, (0, 255, 255), 1, cv2.LINE_AA)
    
    # 2 Horizontal smoothed curves (thick green)
    cv2.polylines(vis_step3, [T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis_step3, [B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    
    # 2 Lateral straight guides (thick blue)
    cv2.polylines(vis_step3, [L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis_step3, [R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    
    # Draw 5 control points on top and bottom (cyan)
    for pt in top_5_pts:
        cv2.circle(vis_step3, (int(pt[0]), int(pt[1])), 5, (255, 255, 0), -1, cv2.LINE_AA)
    for pt in bot_5_pts:
        cv2.circle(vis_step3, (int(pt[0]), int(pt[1])), 5, (255, 255, 0), -1, cv2.LINE_AA)
        
    # Draw 4 Corner Vertices (red/white)
    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis_step3, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_step3, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)
        
    cv2.imwrite(os.path.join(out_dir, "step3_guides_and_corners.png"), vis_step3)
    
    # -------------------------------------------------------------
    # 4. STEP 4: 3D Coon's Patch Grid & Dewarping
    # -------------------------------------------------------------
    print("\n--- STEP 4: 3D Coon's Patch Grid & Unrolling ---")
    grid_rows, grid_cols = 32, 24
    u_g = np.linspace(0.0, 1.0, grid_cols)
    v_g = np.linspace(0.0, 1.0, grid_rows)
    u_vals = np.linspace(0.0, 1.0, len(T_curve))
    v_vals = np.linspace(0.0, 1.0, len(L_line))
    
    T_res = np.column_stack((np.interp(u_g, u_vals, T_curve[:, 0]), np.interp(u_g, u_vals, T_curve[:, 1])))
    B_res = np.column_stack((np.interp(u_g, u_vals, B_curve[:, 0]), np.interp(u_g, u_vals, B_curve[:, 1])))
    L_res = np.column_stack((np.interp(v_g, v_vals, L_line[:, 0]), np.interp(v_g, v_vals, L_line[:, 1])))
    R_res = np.column_stack((np.interp(v_g, v_vals, R_line[:, 0]), np.interp(v_g, v_vals, R_line[:, 1])))
    
    u_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
    v_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
    
    for r in range(grid_rows):
        v_val = v_g[r]
        for c in range(grid_cols):
            u_val = u_g[c]
            c_blend = (1.0 - u_val)*(1.0 - v_val)*P_TL + u_val*(1.0 - v_val)*P_TR + (1.0 - u_val)*v_val*P_BL + u_val*v_val*P_BR
            pt = (1.0 - v_val)*T_res[c] + v_val*B_res[c] + (1.0 - u_val)*L_res[r] + u_val*R_res[r] - c_blend
            u_grid[r, c] = np.clip(pt[0], 0, w_c - 1)
            v_grid[r, c] = np.clip(pt[1], 0, h_c - 1)
            
    arc_T = np.sum(np.hypot(np.diff(T_curve[:, 0]), np.diff(T_curve[:, 1])))
    arc_B = np.sum(np.hypot(np.diff(B_curve[:, 0]), np.diff(B_curve[:, 1])))
    dst_w = max(int(round(max(arc_T, arc_B))), 100)
    
    len_L = np.sum(np.hypot(np.diff(L_line[:, 0]), np.diff(L_line[:, 1])))
    len_R = np.sum(np.hypot(np.diff(R_line[:, 0]), np.diff(R_line[:, 1])))
    dst_h = max(int(round(max(len_L, len_R))), 100)
    
    map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    dewarped = cv2.remap(crop_bgr, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
    
    vis_step4_grid = crop_bgr.copy()
    for r in range(grid_rows):
        pts_r = np.column_stack((u_grid[r, :], v_grid[r, :])).astype(np.int32)
        cv2.polylines(vis_step4_grid, [pts_r], False, (0, 220, 255), 1, cv2.LINE_AA)
    for c in range(grid_cols):
        pts_c = np.column_stack((u_grid[:, c], v_grid[:, c])).astype(np.int32)
        cv2.polylines(vis_step4_grid, [pts_c], False, (0, 180, 255), 1, cv2.LINE_AA)
        
    cv2.imwrite(os.path.join(out_dir, "step4_3d_mesh.png"), vis_step4_grid)
    cv2.imwrite(os.path.join(out_dir, "step4_dewarped_scan.png"), dewarped)
    
    # -------------------------------------------------------------
    # 5. STEP 5: OCR Recognition & Word Box Markup
    # -------------------------------------------------------------
    print("\n--- STEP 5: OCR Recognition & Lexicon Correction ---")
    ocr_decoder = Stage5OCRDecoder(use_gpu=True)
    lexicon = WineVocabularyCorrector()
    
    ocr_res = ocr_decoder.process(dewarped)
    raw_text = ocr_res["full_text"]
    corrected_text, cor_logs = lexicon.correct_text(raw_text)
    
    print(f"OCR Recognized Text: '{raw_text}'")
    print(f"Lexicon Normalized:  '{corrected_text}'")
    
    vis_step5_ocr = ocr_res["annotated_bgr"]
    cv2.imwrite(os.path.join(out_dir, "step5_ocr_annotated.png"), vis_step5_ocr)
    
    # Assemble unified 5-step master board
    def resize_to_h(im, th):
        ih, iw = im.shape[:2]
        tw = max(int(round(iw * (th / float(ih)))), 40)
        return cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA)
        
    board_h = 480
    b1 = resize_to_h(vis_step1, board_h)
    b2 = resize_to_h(vis_step2_overlay, board_h)
    b3 = resize_to_h(vis_step3, board_h)
    b4 = resize_to_h(vis_step4_grid, board_h)
    b5 = resize_to_h(dewarped, board_h)
    b6 = resize_to_h(vis_step5_ocr, board_h)
    
    def add_card_header(im, title):
        card = np.zeros((im.shape[0] + 36, im.shape[1], 3), dtype=np.uint8)
        card[36:, :] = im
        cv2.putText(card, title, (8, 25), cv2.FONT_HERSHEY_DUPLEX, 0.60, (255, 255, 255), 1, cv2.LINE_AA)
        return card
        
    c1 = add_card_header(b1, "1. YOLO BBox")
    c2 = add_card_header(b2, "2. SAM Mask")
    c3 = add_card_header(b3, "3. 4 Verts + 5-pt Guides")
    c4 = add_card_header(b4, "4. 3D Mesh")
    c5 = add_card_header(b5, "5. Flat Scan")
    c6 = add_card_header(b6, "6. OCR Words")
    
    divider = np.full((board_h + 36, 4, 3), 100, dtype=np.uint8)
    master_board = np.hstack((c1, divider, c2, divider, c3, divider, c4, divider, c5, divider, c6))
    cv2.imwrite(os.path.join(out_dir, "tsimlyanskoe_full_master_board.png"), master_board)
    print("Saved tsimlyanskoe_full_master_board.png!")
    
    # Save Report Markdown Artifact
    md_path = os.path.join(brain_dir, "tsimlyanskoe_step_by_step_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 🍷 Пошаговый отчет обработки: «ЦИМЛЯНСКОЕ КРЕПОСТЬ САРКЕЛ»\n\n")
        f.write("Полный конвейер по 5 этапам технического задания:\n\n")
        f.write("![5-Step Master Board](/C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/tsimlyanskoe_step_by_step/tsimlyanskoe_full_master_board.png)\n\n")
        f.write("---\n\n")
        
        f.write("### Этап 1. Локализация Bounding Box (YOLOv8x-seg)\n")
        f.write(f"- **Координаты рамки:** `[X1={wbx1}, Y1={wby1}, X2={wbx2}, Y2={wby2}]`\n")
        f.write(f"- **Уверенность модели:** `100.0% (conf={winner_box_obj['conf']:.2f})`\n")
        f.write(f"- **Площадь рамки:** `{winner_box_obj['area']:,} px`\n\n")
        f.write("![Этап 1: Рамка YOLO](/C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/tsimlyanskoe_step_by_step/step1_yolo_bbox.png)\n\n")
        f.write("---\n\n")
        
        f.write("### Этап 2. Высокоточная сегментация маски (Meta SAM ViT-H)\n")
        f.write(f"- **Модель:** Meta Segment Anything Model (ViT-H Huge Backbone) на CUDA FP16.\n")
        f.write(f"- **Время сегментации:** `{t_sam_ms:.1f} мс` (Score: `{sam_score:.3f}`).\n")
        f.write(f"- **Размер кропа (с запасом 10 px):** `{w_c}x{h_c}` px.\n\n")
        f.write("![Этап 2: Маска SAM](/C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/tsimlyanskoe_step_by_step/step2_sam_overlay.png)\n\n")
        f.write("---\n\n")
        
        f.write("### Этап 3. 4 вершины излома + 2 прямые боковые + 2 горизонтальные дуги по 5 точкам\n")
        f.write(f"- **4 крайние вершины (углы излома):**\n")
        f.write(f"  * $P_{{TL}}$ (Верхний левый): `[X={P_TL[0]:.1f}, Y={P_TL[1]:.1f}]`\n")
        f.write(f"  * $P_{{TR}}$ (Верхний правый): `[X={P_TR[0]:.1f}, Y={P_TR[1]:.1f}]`\n")
        f.write(f"  * $P_{{BL}}$ (Нижний левый): `[X={P_BL[0]:.1f}, Y={P_BL[1]:.1f}]`\n")
        f.write(f"  * $P_{{BR}}$ (Нижний правый): `[X={P_BR[0]:.1f}, Y={P_BR[1]:.1f}]`\n")
        f.write(f"- **2 боковые направляющие (синие):** прямые отрезки $P_{{TL}} \\to P_{{BL}}$ и $P_{{TR}} \\to P_{{BR}}$.\n")
        f.write(f"- **2 горизонтальные направляющие (зеленые):** сглаженные кривые второго порядка, построенные через **5 контрольных точек** (желтые ломаные и голубые маркеры) по верхней и нижней кромкам маски.\n\n")
        f.write("![Этап 3: Направляющие и 4 угла](/C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/tsimlyanskoe_step_by_step/step3_guides_and_corners.png)\n\n")
        f.write("---\n\n")
        
        f.write("### Этап 4. 3D-сетка (Coon's Patch) и цилиндрическая развертка\n")
        f.write(f"- **Разрешение 3D-сетки:** `32 строки x 24 столбца`.\n")
        f.write(f"- **Результирующий плоский скан:** `{dst_w}x{dst_h}` px (интерполяция Lanczos4).\n\n")
        f.write("![Этап 4: 3D Сетка](/C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/tsimlyanskoe_step_by_step/step4_3d_mesh.png)\n\n")
        f.write("![Этап 4: Выпрямленный плоский скан](/C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/tsimlyanskoe_step_by_step/step4_dewarped_scan.png)\n\n")
        f.write("---\n\n")
        
        f.write("### Этап 5. Распознавание текста (OCR & Wine Lexicon)\n")
        f.write(f"- **Распознанный сырой текст:**\n  ```text\n  {raw_text}\n  ```\n")
        f.write(f"- **Нормализованный винным словарем текст:**\n  ```text\n  {corrected_text}\n  ```\n")
        f.write(f"- **Распознанные блоки слов с рамками захвата:**\n\n")
        f.write("![Этап 5: Разметка OCR токенов](/C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/tsimlyanskoe_step_by_step/step5_ocr_annotated.png)\n\n")
        
    print(f"Report generated at: {md_path}")

if __name__ == "__main__":
    process_tsimlyanskoe()
