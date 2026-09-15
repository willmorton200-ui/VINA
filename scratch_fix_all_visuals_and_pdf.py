import os
import cv2
import numpy as np
import json
from PIL import Image as PILImage, ImageDraw, ImageFont

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage3_optimization import Stage3CylinderOptimizer
from pipeline.stage4_remapping import Stage4Remapper
from pipeline.stage5_ocr import Stage5OCRDecoder

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

# Helper function for rendering beautiful Cyrillic text on OpenCV images
def draw_cyrillic_text(img_bgr, text, org, font_size=20, text_color=(255, 255, 255), bg_color=None):
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

# Robust True Boundary & Corner Extractor
def extract_true_boundaries_and_corners(crop_bgr, mask_crop, name=""):
    h, w = crop_bgr.shape[:2]
    
    binary = np.uint8(mask_crop > 127)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels > 2:
        largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        clean_mask = np.zeros_like(mask_crop)
        clean_mask[labels == largest_label] = 255
        mask_crop = clean_mask

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_closed = cv2.morphologyEx(mask_crop, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(contours, key=cv2.contourArea).squeeze(1)
    N_cnt = len(cnt)
    
    ys = cnt[:, 1]
    xs = cnt[:, 0]
    unique_ys = np.sort(np.unique(ys))
    
    left_profile = []
    right_profile = []
    for y_cur in unique_ys:
        xs_at_y = cnt[cnt[:, 1] == y_cur, 0]
        left_profile.append([float(np.min(xs_at_y)), float(y_cur)])
        right_profile.append([float(np.max(xs_at_y)), float(y_cur)])
    left_profile = np.array(left_profile)
    right_profile = np.array(right_profile)
    
    y_min, y_max = np.min(ys), np.max(ys)
    x_min, x_max = np.min(xs), np.max(xs)
    H_mask = y_max - y_min
    W_mask = x_max - x_min
    
    # Corners:
    # Top-Left: leftmost point in top 35%
    cand_tl = left_profile[left_profile[:, 1] <= y_min + 0.35 * H_mask]
    P_TL = cand_tl[np.argmin(cand_tl[:, 0])]
    
    # Top-Right: rightmost point in top 35%
    cand_tr = right_profile[right_profile[:, 1] <= y_min + 0.35 * H_mask]
    P_TR = cand_tr[np.argmax(cand_tr[:, 0])]
    
    # Bottom-Left: the point where the left vertical profile transitions to bottom smile (y around 80-95% height)
    cand_bl = left_profile[(left_profile[:, 1] >= y_min + 0.70 * H_mask) & (left_profile[:, 1] <= y_min + 0.96 * H_mask)]
    # Look for the corner point (where (y - x) is maximized or where contour turns sharply inward)
    if len(cand_bl) > 0:
        # The corner balances maximum depth Y with minimum inward drift X
        scores_bl = (cand_bl[:, 1] - y_min) - 0.7 * (cand_bl[:, 0] - x_min)
        P_BL = cand_bl[np.argmax(scores_bl)]
    else:
        P_BL = left_profile[-1]
        
    # Bottom-Right: the point where right vertical profile transitions to bottom smile
    cand_br = right_profile[(right_profile[:, 1] >= y_min + 0.70 * H_mask) & (right_profile[:, 1] <= y_min + 0.96 * H_mask)]
    if len(cand_br) > 0:
        scores_br = (cand_br[:, 1] - y_min) - 0.7 * (x_max - cand_br[:, 0])
        P_BR = cand_br[np.argmax(scores_br)]
    else:
        P_BR = right_profile[-1]
        
    def find_nearest_contour_idx(pt, cnt_pts):
        dists = np.hypot(cnt_pts[:, 0] - pt[0], cnt_pts[:, 1] - pt[1])
        return int(np.argmin(dists))
        
    i_tl = find_nearest_contour_idx(P_TL, cnt)
    i_tr = find_nearest_contour_idx(P_TR, cnt)
    i_bl = find_nearest_contour_idx(P_BL, cnt)
    i_br = find_nearest_contour_idx(P_BR, cnt)
    
    def get_cnt_segment(s_idx, e_idx):
        if (e_idx - s_idx) % N_cnt < (s_idx - e_idx) % N_cnt:
            return cnt[[(s_idx + i) % N_cnt for i in range((e_idx - s_idx) % N_cnt + 1)]]
        else:
            return cnt[[(s_idx - i) % N_cnt for i in range((s_idx - e_idx) % N_cnt + 1)]]
            
    seg_t1 = get_cnt_segment(i_tl, i_tr)
    seg_t2 = get_cnt_segment(i_tr, i_tl)
    T_raw = seg_t1 if np.mean(seg_t1[:, 1]) < np.mean(seg_t2[:, 1]) else seg_t2
    if T_raw[0, 0] > T_raw[-1, 0]:
        T_raw = T_raw[::-1]
        
    seg_b1 = get_cnt_segment(i_bl, i_br)
    seg_b2 = get_cnt_segment(i_br, i_bl)
    B_raw = seg_b1 if np.mean(seg_b1[:, 1]) > np.mean(seg_b2[:, 1]) else seg_b2
    if B_raw[0, 0] > B_raw[-1, 0]:
        B_raw = B_raw[::-1]
        
    # Side profiles along actual contour
    seg_l1 = get_cnt_segment(i_tl, i_bl)
    seg_l2 = get_cnt_segment(i_bl, i_tl)
    L_raw = seg_l1 if np.mean(seg_l1[:, 0]) < np.mean(seg_l2[:, 0]) else seg_l2
    if L_raw[0, 1] > L_raw[-1, 1]:
        L_raw = L_raw[::-1]
        
    seg_r1 = get_cnt_segment(i_tr, i_br)
    seg_r2 = get_cnt_segment(i_br, i_tr)
    R_raw = seg_r1 if np.mean(seg_r1[:, 0]) > np.mean(seg_r2[:, 0]) else seg_r2
    if R_raw[0, 1] > R_raw[-1, 1]:
        R_raw = R_raw[::-1]
        
    N_pts = 60
    u_vals = np.linspace(0.0, 1.0, N_pts)
    v_vals = np.linspace(0.0, 1.0, N_pts)
    
    T_curve = np.column_stack((
        np.interp(u_vals, np.linspace(0, 1, len(T_raw)), T_raw[:, 0]),
        np.interp(u_vals, np.linspace(0, 1, len(T_raw)), T_raw[:, 1])
    ))
    B_curve = np.column_stack((
        np.interp(u_vals, np.linspace(0, 1, len(B_raw)), B_raw[:, 0]),
        np.interp(u_vals, np.linspace(0, 1, len(B_raw)), B_raw[:, 1])
    ))
    L_curve = np.column_stack((
        np.interp(v_vals, np.linspace(0, 1, len(L_raw)), L_raw[:, 0]),
        np.interp(v_vals, np.linspace(0, 1, len(L_raw)), L_raw[:, 1])
    ))
    R_curve = np.column_stack((
        np.interp(v_vals, np.linspace(0, 1, len(R_raw)), R_raw[:, 0]),
        np.interp(v_vals, np.linspace(0, 1, len(R_raw)), R_raw[:, 1])
    ))
    
    # 3D Coon's Grid
    grid_rows, grid_cols = 24, 32
    u_g = np.linspace(0.0, 1.0, grid_cols)
    v_g = np.linspace(0.0, 1.0, grid_rows)
    
    T_res = np.column_stack((np.interp(u_g, u_vals, T_curve[:, 0]), np.interp(u_g, u_vals, T_curve[:, 1])))
    B_res = np.column_stack((np.interp(u_g, u_vals, B_curve[:, 0]), np.interp(u_g, u_vals, B_curve[:, 1])))
    L_res = np.column_stack((np.interp(v_g, v_vals, L_curve[:, 0]), np.interp(v_g, v_vals, L_curve[:, 1])))
    R_res = np.column_stack((np.interp(v_g, v_vals, R_curve[:, 0]), np.interp(v_g, v_vals, R_curve[:, 1])))
    
    u_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
    v_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
    
    for i in range(grid_rows):
        v = v_g[i]
        for j in range(grid_cols):
            u = u_g[j]
            c_blend = (1.0 - u) * (1.0 - v) * P_TL + u * (1.0 - v) * P_TR + (1.0 - u) * v * P_BL + u * v * P_BR
            pt = (1.0 - v) * T_res[j] + v * B_res[j] + (1.0 - u) * L_res[i] + u * R_res[i] - c_blend
            u_grid[i, j] = np.clip(pt[0], 0, w - 1)
            v_grid[i, j] = np.clip(pt[1], 0, h - 1)
            
    # Compute Natural Unwarped Dimensions
    # Horizontal width = mean arc length
    arc_top = np.sum(np.hypot(np.diff(T_curve[:, 0]), np.diff(T_curve[:, 1])))
    arc_bot = np.sum(np.hypot(np.diff(B_curve[:, 0]), np.diff(B_curve[:, 1])))
    dst_w = int(round(max(arc_top, arc_bot)))
    
    len_left = np.sum(np.hypot(np.diff(L_curve[:, 0]), np.diff(L_curve[:, 1])))
    len_right = np.sum(np.hypot(np.diff(R_curve[:, 0]), np.diff(R_curve[:, 1])))
    dst_h = int(round(max(len_left, len_right)))
    
    # Dense Remap
    map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    dewarped = cv2.remap(crop_bgr, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
    
    # Visualizations
    # Step 3: Vectors & Corners
    vis_step3 = crop_bgr.copy()
    cv2.polylines(vis_step3, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_step3, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    for pt, lbl in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
        px, py = int(pt[0]), int(pt[1])
        cv2.circle(vis_step3, (px, py), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_step3, (px, py), 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_step3, (px, py), 2, (255, 255, 255), -1, cv2.LINE_AA)
        vis_step3 = draw_cyrillic_text(vis_step3, lbl, (px + 10, py - 12), font_size=16, text_color=(0, 255, 255))
        
    # Step 4: Curves
    vis_step4 = vis_step3.copy()
    cv2.polylines(vis_step4, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_step4, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    
    # Step 5: 3D Mesh
    vis_step5 = crop_bgr.copy()
    cv2.polylines(vis_step5, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_step5, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_step5, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_step5, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    for i in range(grid_rows):
        pts_row = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
        cv2.polylines(vis_step5, [pts_row], False, (0, 240, 255), 1, cv2.LINE_AA)
    for j in range(grid_cols):
        pts_col = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
        cv2.polylines(vis_step5, [pts_col], False, (0, 180, 255), 1, cv2.LINE_AA)
    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis_step5, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_step5, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
        
    return {
        "P_TL": P_TL, "P_TR": P_TR, "P_BL": P_BL, "P_BR": P_BR,
        "T_curve": T_curve, "B_curve": B_curve, "L_curve": L_curve, "R_curve": R_curve,
        "u_grid": u_grid, "v_grid": v_grid,
        "vis_step3": vis_step3, "vis_step4": vis_step4, "vis_step5": vis_step5,
        "dewarped": dewarped,
        "dst_w": dst_w, "dst_h": dst_h
    }

# Build High-Quality 6-Step Board with Cyrillic Headers and Perfect Aspect Ratio
def build_clean_board(b_id, title, crop_bgr, mask_crop, geo_res, ocr_dewarped_annotated):
    h_c, w_c = crop_bgr.shape[:2]
    
    # Step 2: Mask overlay
    vis_mask = crop_bgr.copy()
    mask_overlay = np.zeros_like(crop_bgr)
    mask_overlay[mask_crop > 127] = [0, 255, 0]
    vis_step2 = cv2.addWeighted(vis_mask, 0.70, mask_overlay, 0.30, 0)
    y_idxs, x_idxs = np.where(mask_crop > 127)
    cv2.rectangle(vis_step2, (int(np.min(x_idxs)), int(np.min(y_idxs))), (int(np.max(x_idxs)), int(np.max(y_idxs))), (0, 255, 255), 2)
    
    steps = [
        ("1. Исходный кроп", crop_bgr),
        ("2. Точная маска SAM", vis_step2),
        ("3. Боковые образующие", geo_res["vis_step3"]),
        ("4. Верхняя/Нижняя кривые", geo_res["vis_step4"]),
        ("5. 3D Сетка Coon's Patch", geo_res["vis_step5"]),
        ("6. Развертка + OCR", ocr_dewarped_annotated)
    ]
    
    target_h = 450
    row1, row2 = [], []
    
    for idx, (label, img_step) in enumerate(steps):
        h, w = img_step.shape[:2]
        scale = target_h / float(h)
        new_w = int(round(w * scale))
        r = cv2.resize(img_step, (new_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        
        # Cyrillic banner
        banner = np.zeros((45, new_w, 3), dtype=np.uint8) + 28
        banner = draw_cyrillic_text(banner, label, (10, 10), font_size=18, text_color=(0, 255, 255))
        
        card = np.vstack((banner, r))
        card = cv2.copyMakeBorder(card, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=[70, 70, 70])
        
        if idx < 3:
            row1.append(card)
        else:
            row2.append(card)
            
    r1 = np.hstack(row1)
    r2 = np.hstack(row2)
    
    max_w = max(r1.shape[1], r2.shape[1])
    if r1.shape[1] < max_w:
        r1 = cv2.copyMakeBorder(r1, 0, 0, 0, max_w - r1.shape[1], cv2.BORDER_CONSTANT, value=[28, 28, 28])
    if r2.shape[1] < max_w:
        r2 = cv2.copyMakeBorder(r2, 0, 0, 0, max_w - r2.shape[1], cv2.BORDER_CONSTANT, value=[28, 28, 28])
        
    board = np.vstack((r1, r2))
    hdr = np.zeros((55, max_w, 3), dtype=np.uint8) + 18
    hdr = draw_cyrillic_text(hdr, f"VINA v1.2 Пайплайн: {title}", (20, 14), font_size=24, text_color=(255, 255, 255))
    
    final_board = np.vstack((hdr, board))
    out_path = os.path.join(artifacts_dir, f"{b_id}_perfect_pipeline_board.png")
    cv2.imwrite(out_path, final_board)
    print(f"Generated clean board: {out_path} ({final_board.shape[1]}x{final_board.shape[0]})")
    return out_path

print("Helper functions ready!")
