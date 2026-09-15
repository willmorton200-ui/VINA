import cv2
import numpy as np
import os

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-29.jpg')

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()

mask_red, _ = p1.sam_refiner.refine_mask(img, [0, 273, 463, 832])
mask_white, _ = p1.sam_refiner.refine_mask(img, [479, 263, 960, 840])

def detect_exact_corner_quad(crop_bgr, mask_crop, name):
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
    cnt = max(contours, key=cv2.contourArea)
    pts = cnt.squeeze(1) # (N, 2)
    
    x_min, y_min = np.min(pts, axis=0)
    x_max, y_max = np.max(pts, axis=0)
    H_mask = y_max - y_min
    W_mask = x_max - x_min
    
    # 2. Extract left profile and right profile points
    ys = pts[:, 1]
    unique_ys = np.sort(np.unique(ys))
    
    left_pts = []
    right_pts = []
    for y_cur in unique_ys:
        xs_at_y = pts[pts[:, 1] == y_cur, 0]
        left_pts.append([float(np.min(xs_at_y)), float(y_cur)])
        right_pts.append([float(np.max(xs_at_y)), float(y_cur)])
    left_pts = np.array(left_pts)
    right_pts = np.array(right_pts)
    
    # 3. Fit stable lateral lines (generators) using the vertical middle section (25% to 75% height)
    mid_L = left_pts[(left_pts[:, 1] >= y_min + 0.25 * H_mask) & (left_pts[:, 1] <= y_min + 0.75 * H_mask)]
    mid_R = right_pts[(right_pts[:, 1] >= y_min + 0.25 * H_mask) & (right_pts[:, 1] <= y_min + 0.75 * H_mask)]
    
    poly_L = np.polyfit(mid_L[:, 1], mid_L[:, 0], deg=1) # x = m*y + c
    poly_R = np.polyfit(mid_R[:, 1], mid_R[:, 0], deg=1)
    
    # 4. Find the points belonging to Left Lateral Line:
    # A point on left_pts belongs to the left line if |x - (m_L * y + c_L)| <= tolerance (e.g. 7 px)
    dist_L_all = np.abs(left_pts[:, 0] - (poly_L[0] * left_pts[:, 1] + poly_L[1]))
    on_left_line = left_pts[dist_L_all <= 8.0]
    
    # Top-Left corner: the uppermost point (min Y) on the left line
    P_TL = on_left_line[np.argmin(on_left_line[:, 1])]
    # Bottom-Left corner: the lowermost point (max Y) on the left line
    P_BL = on_left_line[np.argmax(on_left_line[:, 1])]
    
    # Same for Right Lateral Line:
    dist_R_all = np.abs(right_pts[:, 0] - (poly_R[0] * right_pts[:, 1] + poly_R[1]))
    on_right_line = right_pts[dist_R_all <= 8.0]
    
    P_TR = on_right_line[np.argmin(on_right_line[:, 1])]
    P_BR = on_right_line[np.argmax(on_right_line[:, 1])]
    
    print(f"[{name}] Detected Corners:")
    print(f"  P_TL: {P_TL.round(1)} | P_TR: {P_TR.round(1)}")
    print(f"  P_BL: {P_BL.round(1)} | P_BR: {P_BR.round(1)}")
    
    # 5. Extract continuous Top Curve between P_TL and P_TR, Bottom Curve between P_BL and P_BR
    def find_nearest_contour_idx(pt, cnt_pts):
        dists = np.hypot(cnt_pts[:, 0] - pt[0], cnt_pts[:, 1] - pt[1])
        return int(np.argmin(dists))
        
    idx_TL = find_nearest_contour_idx(P_TL, pts)
    idx_TR = find_nearest_contour_idx(P_TR, pts)
    idx_BL = find_nearest_contour_idx(P_BL, pts)
    idx_BR = find_nearest_contour_idx(P_BR, pts)
    
    N_cnt = len(pts)
    
    # Path 1 vs Path 2 on closed contour
    def get_segment(i_start, i_end):
        if (i_end - i_start) % N_cnt < (i_start - i_end) % N_cnt:
            return pts[[(i_start + i) % N_cnt for i in range((i_end - i_start) % N_cnt + 1)]]
        else:
            return pts[[(i_start - i) % N_cnt for i in range((i_start - i_end) % N_cnt + 1)]]
            
    seg1 = get_segment(idx_TL, idx_TR)
    # The top curve is the segment where average y is in the upper half of mask
    seg1_alt = get_segment(idx_TR, idx_TL)
    T_pts = seg1 if np.mean(seg1[:, 1]) < np.mean(seg1_alt[:, 1]) else seg1_alt
    
    seg_b1 = get_segment(idx_BL, idx_BR)
    seg_b1_alt = get_segment(idx_BR, idx_BL)
    B_pts = seg_b1 if np.mean(seg_b1[:, 1]) > np.mean(seg_b1_alt[:, 1]) else seg_b1_alt
    
    if T_pts[0, 0] > T_pts[-1, 0]:
        T_pts = T_pts[::-1]
    if B_pts[0, 0] > B_pts[-1, 0]:
        B_pts = B_pts[::-1]
        
    N_pts = 60
    u_vals = np.linspace(0.0, 1.0, N_pts)
    idx_t = np.linspace(0.0, 1.0, len(T_pts))
    T_curve = np.column_stack((np.interp(u_vals, idx_t, T_pts[:, 0]), np.interp(u_vals, idx_t, T_pts[:, 1])))
    
    idx_b = np.linspace(0.0, 1.0, len(B_pts))
    B_curve = np.column_stack((np.interp(u_vals, idx_b, B_pts[:, 0]), np.interp(u_vals, idx_b, B_pts[:, 1])))
    
    v_vals = np.linspace(0.0, 1.0, N_pts)
    L_line = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
    R_line = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR
    
    # 6. Visualization
    vis = crop_bgr.copy()
    # Draw lateral lines (Blue)
    cv2.polylines(vis, [L_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [R_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    
    # Draw top and bottom curves (Green)
    cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    
    # Draw corners with red circles and crosshairs
    for pt, lbl in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
        px, py = int(pt[0]), int(pt[1])
        cv2.circle(vis, (px, py), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (px, py), 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.line(vis, (px - 15, py), (px + 15, py), (0, 255, 255), 2, cv2.LINE_AA)
        cv2.line(vis, (px, py - 15), (px, py + 15), (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(vis, lbl, (px + 12, py - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)
        
    # 3D mesh
    from pipeline.stage3_optimization import Stage3CylinderOptimizer
    from pipeline.stage4_remapping import Stage4Remapper
    from pipeline.stage5_ocr import Stage5OCRDecoder
    
    optimizer = Stage3CylinderOptimizer(grid_rows=24, grid_cols=32)
    remapper = Stage4Remapper()
    ocr = Stage5OCRDecoder(use_gpu=True)
    
    boundaries = {
        "P_TL": P_TL, "P_TR": P_TR, "P_BL": P_BL, "P_BR": P_BR,
        "T_curve_xs": T_curve[:, 0], "T_curve_ys": T_curve[:, 1],
        "B_curve_xs": B_curve[:, 0], "B_curve_ys": B_curve[:, 1],
        "L_curve": L_line, "R_curve": R_line
    }
    res_s3 = optimizer.process(crop_bgr, [], [], {}, mask_crop, boundaries)
    vis_mesh = res_s3["vis_mesh"]
    
    res_s4 = remapper.process(crop_bgr, res_s3)
    dewarped = res_s4["dewarped_bgr"]
    ocr_res = ocr.process(dewarped)
    print(f"  OCR: {ocr_res['full_text']}")
    
    cv2.imwrite(os.path.join(artifacts_dir, f"{name}_perfect_corners.png"), vis)
    cv2.imwrite(os.path.join(artifacts_dir, f"{name}_perfect_mesh.png"), vis_mesh)
    cv2.imwrite(os.path.join(artifacts_dir, f"{name}_perfect_dewarped.png"), dewarped)
    cv2.imwrite(os.path.join(artifacts_dir, f"{name}_perfect_ocr.png"), ocr_res["annotated_bgr"])

detect_exact_corner_quad(img[240:860, 460:960], mask_white[240:860, 460:960], "white")
detect_exact_corner_quad(img[250:850, 0:470], mask_red[250:850, 0:470], "red")
print("\nDone perfect corner quad test!")
