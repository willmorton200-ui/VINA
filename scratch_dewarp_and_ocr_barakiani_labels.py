import cv2
import numpy as np
import os
import json
from PIL import Image as PILImage, ImageDraw, ImageFont

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage5_ocr import Stage5OCRDecoder

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

def draw_cyrillic(img_bgr, text, org, font_size=16, text_color=(255, 255, 255), bg_color=None):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    font_path = r"C:\Windows\Fonts\arialbd.ttf"
    if not os.path.exists(font_path):
        font_path = r"C:\Windows\Fonts\arial.ttf"
    font = ImageFont.truetype(font_path, font_size)
    if bg_color is not None:
        bbox = draw.textbbox(org, text, font=font)
        draw.rectangle(bbox, fill=bg_color)
    draw.text(org, text, font=font, fill=text_color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

# Initialize modules
p1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()
ocr_decoder = Stage5OCRDecoder(use_gpu=True)

img_full = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')
h_img, w_img = img_full.shape[:2]

labels_to_process = [
    {
        "name": "Верхняя этикетка: BARAKIANI",
        "key": "upper",
        "bbox": [239, 366, 673, 685],
        "crop_pad": [220, 345, 690, 700]
    },
    {
        "name": "Нижняя этикетка: САПЕРАВИ (SAPERAVI)",
        "key": "lower",
        "bbox": [241, 670, 654, 1115],
        "crop_pad": [225, 650, 670, 1130]
    }
]

board_cards = []
summary_results = []

for l_info in labels_to_process:
    lbl_name = l_info["name"]
    lbl_key = l_info["key"]
    bbox = l_info["bbox"]
    cx1, cy1, cx2, cy2 = l_info["crop_pad"]
    
    print(f"\n=======================================================")
    print(f"Processing: {lbl_name}")
    print(f"=======================================================")
    
    # 1. SAM Refined Mask
    mask_full, _ = p1.sam_refiner.refine_mask(img_full, bbox)
    crop_bgr = img_full[cy1:cy2, cx1:cx2].copy()
    mask_crop = mask_full[cy1:cy2, cx1:cx2].copy()
    h_c, w_c = crop_bgr.shape[:2]
    
    # 2. Vectorization (Universal Minimum Internal Angle Corners)
    vec = vectorizer.vectorize(mask_crop)
    P_TL, P_TR, P_BL, P_BR = vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR
    T_curve, B_curve = vec.T_curve, vec.B_curve
    L_line, R_line = vec.L_line, vec.R_line
    
    # 3. 3D Coon's Patch Grid Generation
    grid_rows, grid_cols = 24, 32
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
            
    # 4. Dense Remap with Natural Aspect Ratio
    arc_T = np.sum(np.hypot(np.diff(T_curve[:, 0]), np.diff(T_curve[:, 1])))
    arc_B = np.sum(np.hypot(np.diff(B_curve[:, 0]), np.diff(B_curve[:, 1])))
    dst_w = int(round(max(arc_T, arc_B)))
    
    len_L = np.sum(np.hypot(np.diff(L_line[:, 0]), np.diff(L_line[:, 1])))
    len_R = np.sum(np.hypot(np.diff(R_line[:, 0]), np.diff(R_line[:, 1])))
    dst_h = int(round(max(len_L, len_R)))
    
    map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    dewarped = cv2.remap(crop_bgr, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
    
    # 5. OCR on Raw Crop vs Dewarped Scan
    ocr_raw = ocr_decoder.process(crop_bgr)
    ocr_dew = ocr_decoder.process(dewarped)
    
    raw_words = ocr_raw["text_blocks"]
    dew_words = ocr_dew["text_blocks"]
    raw_conf = np.mean([b["confidence"] for b in raw_words]) * 100.0 if raw_words else 0.0
    dew_conf = np.mean([b["confidence"] for b in dew_words]) * 100.0 if dew_words else 0.0
    
    print(f"  [RAW OCR]      {len(raw_words)} words | Conf: {raw_conf:.1f}% | Text: {ocr_raw['full_text']}")
    print(f"  [DEWARPED OCR] {len(dew_words)} words | Conf: {dew_conf:.1f}% | Text: {ocr_dew['full_text']}")
    
    # 6. Create Visual Cards
    vis_p1 = ocr_raw["annotated_bgr"].copy()
    
    vis_p2 = crop_bgr.copy()
    cv2.polylines(vis_p2, [L_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_p2, [R_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_p2, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_p2, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    for pt, lbl in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
        px, py = int(pt[0]), int(pt[1])
        cv2.circle(vis_p2, (px, py), 8, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_p2, (px, py), 5, (0, 0, 255), -1, cv2.LINE_AA)
        vis_p2 = draw_cyrillic(vis_p2, lbl, (px + 6, py - 6), font_size=13, text_color=(0, 255, 255), bg_color=(20, 20, 20))
        
    vis_p3 = crop_bgr.copy()
    cv2.polylines(vis_p3, [L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis_p3, [R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis_p3, [T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis_p3, [B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    for r in range(grid_rows):
        pts_r = np.column_stack((u_grid[r, :], v_grid[r, :])).astype(np.int32)
        cv2.polylines(vis_p3, [pts_r], False, (0, 230, 255), 1, cv2.LINE_AA)
    for c in range(grid_cols):
        pts_c = np.column_stack((u_grid[:, c], v_grid[:, c])).astype(np.int32)
        cv2.polylines(vis_p3, [pts_c], False, (0, 180, 255), 1, cv2.LINE_AA)
        
    vis_p4 = ocr_dew["annotated_bgr"].copy()
    
    # Scale cards
    h_panel = 420
    def scale_p(im):
        w_t = int(round(im.shape[1] * (h_panel / float(im.shape[0]))))
        return cv2.resize(im, (w_t, h_panel), interpolation=cv2.INTER_LANCZOS4)
        
    def make_card(im, header_text, col):
        im_s = scale_p(im)
        banner = np.zeros((38, im_s.shape[1], 3), dtype=np.uint8) + 26
        banner = draw_cyrillic(banner, header_text, (8, 9), font_size=13, text_color=col)
        c = np.vstack((banner, im_s))
        return cv2.copyMakeBorder(c, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=[60, 60, 60])
        
    card1 = make_card(vis_p1, f"1. Исходник + OCR ({len(raw_words)} сл)", (255, 160, 160))
    card2 = make_card(vis_p2, f"2. Направляющие T, B, L, R", (0, 255, 255))
    card3 = make_card(vis_p3, f"3. 3D Сетка Coon's Patch", (0, 220, 255))
    card4 = make_card(vis_p4, f"4. Развертка + OCR ({len(dew_words)} сл, {dew_conf:.0f}%)", (120, 255, 120))
    
    row_b = np.hstack((card1, card2, card3, card4))
    hdr = np.zeros((46, row_b.shape[1], 3), dtype=np.uint8) + 16
    hdr = draw_cyrillic(hdr, f"{lbl_name} | Развертка: {dst_w}x{dst_h} px | Уверенность: {dew_conf:.1f}%", (16, 12), font_size=16, text_color=(255, 255, 255))
    board_lbl = np.vstack((hdr, row_b))
    
    board_out_path = os.path.join(artifacts_dir, f"barakiani_{lbl_key}_label_dewarp_ocr_board.png")
    cv2.imwrite(board_out_path, board_lbl)
    
    # Save individual clean dewarped scan
    dewarp_scan_path = os.path.join(artifacts_dir, f"barakiani_{lbl_key}_dewarped_scan.png")
    cv2.imwrite(dewarp_scan_path, dewarped)
    
    summary_results.append({
        "label": lbl_name,
        "key": lbl_key,
        "dewarped_dims": f"{dst_w}x{dst_h}",
        "raw_ocr_text": ocr_raw["full_text"],
        "dewarped_ocr_text": ocr_dew["full_text"],
        "raw_conf": raw_conf,
        "dew_conf": dew_conf,
        "raw_words_count": len(raw_words),
        "dew_words_count": len(dew_words),
        "board_path": board_out_path,
        "scan_path": dewarp_scan_path
    })

# Save JSON result
with open(os.path.join(artifacts_dir, "barakiani_dewarp_ocr_results.json"), "w", encoding="utf-8") as f:
    json.dump(summary_results, f, ensure_ascii=False, indent=2)

print("\nSuccessfully processed both Barakiani labels!")
