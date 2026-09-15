import os
import glob
import cv2
import numpy as np
import json
import time
from PIL import Image as PILImage, ImageDraw, ImageFont

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage3_optimization import Stage3CylinderOptimizer
from pipeline.stage4_remapping import Stage4Remapper
from pipeline.stage5_ocr import Stage5OCRDecoder

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)
boards_dir = os.path.join(artifacts_dir, "batch_20_boards")
os.makedirs(boards_dir, exist_ok=True)

# Helper function to draw Cyrillic text
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

# Initialize pipeline modules on GPU
print("Initializing VINA Pipeline Modules on GPU...")
p1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()
ocr_decoder = Stage5OCRDecoder(use_gpu=True)

# Get 20 bottle files from test_dataset/butilki
butilki_dir = "test_dataset/butilki"
all_files = sorted([f for f in os.listdir(butilki_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
selected_files = all_files[:20]

print(f"Selected 20 bottles for benchmarking:")
for idx, f in enumerate(selected_files):
    print(f"  {idx+1:2d}. {f}")

results = []
summary_stats = {
    "total_bottles": len(selected_files),
    "raw_total_words": 0,
    "dewarped_total_words": 0,
    "raw_avg_conf": 0.0,
    "dewarped_avg_conf": 0.0,
    "items": []
}

raw_confs_all = []
dew_confs_all = []

for idx, fname in enumerate(selected_files):
    b_num = idx + 1
    fpath = os.path.join(butilki_dir, fname)
    print(f"\n=======================================================")
    print(f"[{b_num:2d}/20] Processing: {fname}")
    print(f"=======================================================")
    
    img_bgr = cv2.imread(fpath)
    if img_bgr is None:
        print(f"Error: could not read {fpath}")
        continue
    h_orig, w_orig = img_bgr.shape[:2]
    
    # 1. Stage 1: Segment bottle & label
    t0 = time.time()
    cropped_bgr, mask_crop, bbox_info = p1.segment_bottle_and_label(img_bgr)
    h_c, w_c = cropped_bgr.shape[:2]
    
    # 2. Stage 2: Universal Vectorization with Minimum Internal Angle Corners
    vec = vectorizer.vectorize(mask_crop)
    P_TL, P_TR, P_BL, P_BR = vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR
    T_curve, B_curve = vec.T_curve, vec.B_curve
    L_line, R_line = vec.L_line, vec.R_line
    
    # 3. Stage 3: 3D Coon's Patch Grid Generation
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
            
    # 4. Stage 4: Dense Remapping with Natural Physical Metric Proportions
    arc_T = np.sum(np.hypot(np.diff(T_curve[:, 0]), np.diff(T_curve[:, 1])))
    arc_B = np.sum(np.hypot(np.diff(B_curve[:, 0]), np.diff(B_curve[:, 1])))
    dst_w = int(round(max(arc_T, arc_B)))
    
    len_L = np.sum(np.hypot(np.diff(L_line[:, 0]), np.diff(L_line[:, 1])))
    len_R = np.sum(np.hypot(np.diff(R_line[:, 0]), np.diff(R_line[:, 1])))
    dst_h = int(round(max(len_L, len_R)))
    
    dst_w = max(dst_w, 100)
    dst_h = max(dst_h, 100)
    
    map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    dewarped = cv2.remap(cropped_bgr, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
    
    # 5. Stage 5: OCR Comparison (Raw Crop vs Dewarped Scan)
    ocr_raw = ocr_decoder.process(cropped_bgr)
    ocr_dew = ocr_decoder.process(dewarped)
    t_proc = time.time() - t0
    
    raw_words = ocr_raw["text_blocks"]
    dew_words = ocr_dew["text_blocks"]
    
    raw_count = len(raw_words)
    dew_count = len(dew_words)
    
    raw_conf = np.mean([b["confidence"] for b in raw_words]) if raw_words else 0.0
    dew_conf = np.mean([b["confidence"] for b in dew_words]) if dew_words else 0.0
    
    raw_confs_all.append(raw_conf)
    dew_confs_all.append(dew_conf)
    summary_stats["raw_total_words"] += raw_count
    summary_stats["dewarped_total_words"] += dew_count
    
    print(f"  Raw OCR:      {raw_count:2d} words | Avg Conf: {raw_conf:.1f}% | Text: {ocr_raw['full_text'][:60]}...")
    print(f"  Dewarped OCR: {dew_count:2d} words | Avg Conf: {dew_conf:.1f}% | Text: {ocr_dew['full_text'][:60]}...")
    print(f"  Corners: TL={P_TL.astype(int)}, TR={P_TR.astype(int)}, BL={P_BL.astype(int)}, BR={P_BR.astype(int)}")
    
    # 6. Generate 4-Panel Visual Board
    # Panel 1: Raw Crop + OCR Annotations
    vis_p1 = ocr_raw["annotated_bgr"].copy()
    
    # Panel 2: Mask + Guide Vectors Overlay
    vis_p2 = cropped_bgr.copy()
    cv2.polylines(vis_p2, [L_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_p2, [R_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_p2, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_p2, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    for pt, lbl in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
        px, py = int(pt[0]), int(pt[1])
        cv2.circle(vis_p2, (px, py), 8, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_p2, (px, py), 6, (0, 0, 255), -1, cv2.LINE_AA)
        vis_p2 = draw_cyrillic(vis_p2, lbl, (px + 6, py - 6), font_size=14, text_color=(0, 255, 255), bg_color=(20, 20, 20))
        
    # Panel 3: 3D Coon's Grid on Crop
    vis_p3 = cropped_bgr.copy()
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
        
    # Panel 4: Dewarped Scan + OCR Annotations
    vis_p4 = ocr_dew["annotated_bgr"].copy()
    
    # Scale panels to uniform height
    h_panel = 480
    def scale_p(im):
        w_t = int(round(im.shape[1] * (h_panel / float(im.shape[0]))))
        return cv2.resize(im, (w_t, h_panel), interpolation=cv2.INTER_LANCZOS4)
        
    def make_card(im, header_text, col):
        im_s = scale_p(im)
        banner = np.zeros((42, im_s.shape[1], 3), dtype=np.uint8) + 26
        banner = draw_cyrillic(banner, header_text, (8, 10), font_size=14, text_color=col)
        c = np.vstack((banner, im_s))
        return cv2.copyMakeBorder(c, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=[60, 60, 60])
        
    card1 = make_card(vis_p1, f"1. Исходник + OCR ({raw_count} сл, {raw_conf:.0f}%)", (255, 160, 160))
    card2 = make_card(vis_p2, f"2. Направляющие T,B,L,R", (0, 255, 255))
    card3 = make_card(vis_p3, f"3. 3D Сетка Coon's Patch", (0, 220, 255))
    card4 = make_card(vis_p4, f"4. Развертка + OCR ({dew_count} сл, {dew_conf:.0f}%)", (120, 255, 120))
    
    row_board = np.hstack((card1, card2, card3, card4))
    hdr = np.zeros((50, row_board.shape[1], 3), dtype=np.uint8) + 16
    hdr = draw_cyrillic(hdr, f"Образец #{b_num:02d}: {fname} | Прирост слов: {dew_count - raw_count:+d} | Разрешение: {dst_w}x{dst_h}", (18, 13), font_size=18, text_color=(255, 255, 255))
    board = np.vstack((hdr, row_board))
    
    board_filename = f"bottle_{b_num:02d}_comparison_board.png"
    board_path = os.path.join(boards_dir, board_filename)
    cv2.imwrite(board_path, board)
    
    item_res = {
        "bottle_num": b_num,
        "filename": fname,
        "board_filename": board_filename,
        "board_path": board_path,
        "crop_w": w_c, "crop_h": h_c,
        "dewarped_w": dst_w, "dewarped_h": dst_h,
        "corners": {
            "P_TL": P_TL.tolist(), "P_TR": P_TR.tolist(),
            "P_BL": P_BL.tolist(), "P_BR": P_BR.tolist()
        },
        "raw_ocr": {
            "word_count": raw_count,
            "avg_confidence": float(raw_conf),
            "full_text": ocr_raw["full_text"],
            "words": [w["text"] for w in raw_words]
        },
        "dewarped_ocr": {
            "word_count": dew_count,
            "avg_confidence": float(dew_conf),
            "full_text": ocr_dew["full_text"],
            "words": [w["text"] for w in dew_words]
        },
        "gain_words": dew_count - raw_count,
        "gain_conf": float(dew_conf - raw_conf),
        "proc_time_sec": float(t_proc)
    }
    summary_stats["items"].append(item_res)

summary_stats["raw_avg_conf"] = float(np.mean(raw_confs_all))
summary_stats["dewarped_avg_conf"] = float(np.mean(dew_confs_all))

json_out_path = os.path.join(artifacts_dir, "batch_20_benchmark_results.json")
with open(json_out_path, "w", encoding="utf-8") as f:
    json.dump(summary_stats, f, ensure_ascii=False, indent=2)

print("\n=======================================================")
print(f"BENCHMARK COMPLETE (20 Bottles Processed)")
print(f"Total Words (Raw Direct Crop):   {summary_stats['raw_total_words']} words")
print(f"Total Words (Dewarped v1.2):     {summary_stats['dewarped_total_words']} words (+{summary_stats['dewarped_total_words'] - summary_stats['raw_total_words']} words, +{(summary_stats['dewarped_total_words'] - summary_stats['raw_total_words']) / max(summary_stats['raw_total_words'], 1) * 100:.1f}%)")
print(f"Average Confidence (Raw Direct): {summary_stats['raw_avg_conf']:.1f}%")
print(f"Average Confidence (Dewarped):   {summary_stats['dewarped_avg_conf']:.1f}% (+{summary_stats['dewarped_avg_conf'] - summary_stats['raw_avg_conf']:.1f}%)")
print(f"Results saved to: {json_out_path}")
print(f"Boards saved to:  {boards_dir}")
