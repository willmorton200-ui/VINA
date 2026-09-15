import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-29.jpg')

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()

mask_red, _ = p1.sam_refiner.refine_mask(img, [0, 273, 463, 832])
mask_white, _ = p1.sam_refiner.refine_mask(img, [479, 263, 960, 840])

def extract_true_4boundary_mask(crop_bgr, mask_crop, name):
    h, w = crop_bgr.shape[:2]
    
    # 1. Clean mask
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
    cnt = max(contours, key=cv2.contourArea).squeeze(1) # (N, 2)
    N_cnt = len(cnt)
    
    # 2. Extract row-by-row profile points
    ys = cnt[:, 1]
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
    x_min, x_max = np.min(cnt[:, 0]), np.max(cnt[:, 0])
    H_mask = y_max - y_min
    W_mask = x_max - x_min
    
    # 3. Find 4 TRUE Corner Inflection Points on the contour:
    # Top-Left: leftmost point in the top 35% of height
    top_left_zone = left_profile[left_profile[:, 1] <= y_min + 0.35 * H_mask]
    P_TL = top_left_zone[np.argmin(top_left_zone[:, 0])] # furthest left
    
    # Top-Right: rightmost point in top 35% of height
    top_right_zone = right_profile[right_profile[:, 1] <= y_min + 0.35 * H_mask]
    P_TR = top_right_zone[np.argmax(top_right_zone[:, 0])] # furthest right
    
    # Bottom-Left: the point in lower 40% where left contour turns from vertical/silhouette into horizontal bottom smile
    bot_left_zone = left_profile[(left_profile[:, 1] >= y_min + 0.60 * H_mask) & (left_profile[:, 1] <= y_min + 0.98 * H_mask)]
    # Look at angle / derivative dx/dy: where dx/dy changes rapidly
    dx_L = np.gradient(bot_left_zone[:, 0], bot_left_zone[:, 1])
    # The corner is where dx/dy starts increasing sharply (turning inward)
    idx_bl_turn = np.where(dx_L > 0.45)[0]
    if len(idx_bl_turn) > 0:
        P_BL = bot_left_zone[idx_bl_turn[0]]
    else:
        P_BL = bot_left_zone[np.argmax(bot_left_zone[:, 1])]
        
    # Bottom-Right: the point in lower 40% where right contour turns from vertical into horizontal bottom smile
    bot_right_zone = right_profile[(right_profile[:, 1] >= y_min + 0.60 * H_mask) & (right_profile[:, 1] <= y_min + 0.98 * H_mask)]
    dx_R = np.gradient(bot_right_zone[:, 0], bot_right_zone[:, 1])
    idx_br_turn = np.where(dx_R < -0.45)[0]
    if len(idx_br_turn) > 0:
        P_BR = bot_right_zone[idx_br_turn[0]]
    else:
        P_BR = bot_right_zone[np.argmax(bot_right_zone[:, 1])]

    print(f"[{name}] True 4 Corners:")
    print(f"  P_TL: {P_TL.round(1)} | P_TR: {P_TR.round(1)}")
    print(f"  P_BL: {P_BL.round(1)} | P_BR: {P_BR.round(1)}")
    
    # 4. Extract the 4 TRUE boundary segments along the contour:
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
            
    # Segment 1: Top Curve (between TL and TR)
    seg_t1 = get_cnt_segment(i_tl, i_tr)
    seg_t2 = get_cnt_segment(i_tr, i_tl)
    T_raw = seg_t1 if np.mean(seg_t1[:, 1]) < np.mean(seg_t2[:, 1]) else seg_t2
    if T_raw[0, 0] > T_raw[-1, 0]:
        T_raw = T_raw[::-1]
        
    # Segment 2: Bottom Curve (between BL and BR)
    seg_b1 = get_cnt_segment(i_bl, i_br)
    seg_b2 = get_cnt_segment(i_br, i_bl)
    B_raw = seg_b1 if np.mean(seg_b1[:, 1]) > np.mean(seg_b2[:, 1]) else seg_b2
    if B_raw[0, 0] > B_raw[-1, 0]:
        B_raw = B_raw[::-1]
        
    # Segment 3: Left Curve (between TL and BL) - follows the actual silhouette!
    seg_l1 = get_cnt_segment(i_tl, i_bl)
    seg_l2 = get_cnt_segment(i_bl, i_tl)
    L_raw = seg_l1 if np.mean(seg_l1[:, 0]) < np.mean(seg_l2[:, 0]) else seg_l2
    if L_raw[0, 1] > L_raw[-1, 1]:
        L_raw = L_raw[::-1] # from top (min Y) to bottom (max Y)
        
    # Segment 4: Right Curve (between TR and BR)
    seg_r1 = get_cnt_segment(i_tr, i_br)
    seg_r2 = get_cnt_segment(i_br, i_tr)
    R_raw = seg_r1 if np.mean(seg_r1[:, 0]) > np.mean(seg_r2[:, 0]) else seg_r2
    if R_raw[0, 1] > R_raw[-1, 1]:
        R_raw = R_raw[::-1]
        
    # Resample all 4 curves to N_pts
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
    
    # 5. Build Coon's Patch 3D Grid
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
            
    # Calculate Natural Physical Aspect Ratio
    # Real arc width = mean length of top and bottom curves
    arc_top = np.sum(np.hypot(np.diff(T_curve[:, 0]), np.diff(T_curve[:, 1])))
    arc_bot = np.sum(np.hypot(np.diff(B_curve[:, 0]), np.diff(B_curve[:, 1])))
    dst_w = int(max(arc_top, arc_bot))
    
    len_left = np.sum(np.hypot(np.diff(L_curve[:, 0]), np.diff(L_curve[:, 1])))
    len_right = np.sum(np.hypot(np.diff(R_curve[:, 0]), np.diff(R_curve[:, 1])))
    dst_h = int(max(len_left, len_right))
    
    print(f"[{name}] Natural Aspect Ratio Dimensions: W={dst_w}, H={dst_h} (AR={dst_w/dst_h:.2f})")
    
    # 6. Rectification / Dewarping with True Aspect Ratio
    from scipy.interpolate import RegularGridInterpolator
    from pipeline.stage4_remapping import Stage4Remapper
    
    # Remap meshgrid
    grid_y_flat, grid_x_flat = np.meshgrid(
        np.linspace(0, dst_h - 1, grid_rows),
        np.linspace(0, dst_w - 1, grid_cols),
        indexing='ij'
    )
    src_ctrl_pts = np.column_stack((u_grid.ravel(), v_grid.ravel())).astype(np.float32)
    dst_ctrl_pts = np.column_stack((grid_x_flat.ravel(), grid_y_flat.ravel())).astype(np.float32)
    
    # Dense maps
    map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
    
    dewarped = cv2.remap(crop_bgr, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
    
    # Visual overlay
    vis_mesh = crop_bgr.copy()
    # Left and Right blue boundary lines (exact contour silhouette)
    cv2.polylines(vis_mesh, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_mesh, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    # Top and bottom green curves
    cv2.polylines(vis_mesh, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis_mesh, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    
    # Internal grid lines
    for i in range(grid_rows):
        pts_row = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
        cv2.polylines(vis_mesh, [pts_row], False, (0, 240, 255), 1, cv2.LINE_AA)
    for j in range(grid_cols):
        pts_col = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
        cv2.polylines(vis_mesh, [pts_col], False, (0, 180, 255), 1, cv2.LINE_AA)
        
    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
        
    return {
        "vis_mesh": vis_mesh,
        "dewarped": dewarped,
        "dst_w": dst_w,
        "dst_h": dst_h,
        "P_TL": P_TL, "P_TR": P_TR, "P_BL": P_BL, "P_BR": P_BR
    }

res_red = extract_true_4boundary_mask(img[250:850, 0:470], mask_red[250:850, 0:470], "Castillo_Red")
res_white = extract_true_4boundary_mask(img[240:860, 460:960], mask_white[240:860, 460:960], "Castillo_White")

cv2.imwrite(os.path.join(artifacts_dir, "castillo_red_true_contour_mesh.png"), res_red["vis_mesh"])
cv2.imwrite(os.path.join(artifacts_dir, "castillo_red_true_aspect_dewarped.png"), res_red["dewarped"])
cv2.imwrite(os.path.join(artifacts_dir, "castillo_white_true_contour_mesh.png"), res_white["vis_mesh"])
cv2.imwrite(os.path.join(artifacts_dir, "castillo_white_true_aspect_dewarped.png"), res_white["dewarped"])

print("Successfully generated true contour mesh and true aspect ratio dewarped scans!")
