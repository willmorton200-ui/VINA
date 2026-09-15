import cv2
import numpy as np
import os

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-29.jpg')

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()

mask_red, _ = p1.sam_refiner.refine_mask(img, [0, 273, 463, 832])
mask_white, _ = p1.sam_refiner.refine_mask(img, [479, 263, 960, 840])

def find_exact_corners_robust(mask: np.ndarray) -> dict:
    """
    Robust 4-Corner and Lateral Profile Detector:
    1. Extracts outer closed contour of the mask.
    2. Identifies vertical lateral generators (L and R) via directional filtering.
    3. Finds exact inflection points (P_TL, P_TR, P_BL, P_BR) via contour curvature and directional transitions.
    4. Extracts exact top and bottom boundary curves T(u) and B(u) between corners.
    """
    h, w = mask.shape[:2]
    
    # 1. Clean mask
    binary = np.uint8(mask > 127)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels > 2:
        largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        clean_mask = np.zeros_like(mask)
        clean_mask[labels == largest_label] = 255
        mask = clean_mask

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    pts = cnt.squeeze(1) # (N, 2)
    
    # Find bounding box
    x_min, y_min = np.min(pts, axis=0)
    x_max, y_max = np.max(pts, axis=0)
    H_mask = y_max - y_min
    W_mask = x_max - x_min
    
    # Extract left-most and right-most points for every Y
    ys = pts[:, 1]
    unique_ys = np.sort(np.unique(ys))
    
    left_profile = []
    right_profile = []
    for y_cur in unique_ys:
        xs_at_y = pts[pts[:, 1] == y_cur, 0]
        left_profile.append([float(np.min(xs_at_y)), float(y_cur)])
        right_profile.append([float(np.max(xs_at_y)), float(y_cur)])
    left_profile = np.array(left_profile)
    right_profile = np.array(right_profile)
    
    # 2. Fit lateral lines in the stable middle region (20% to 75% height)
    mid_mask_L = (left_profile[:, 1] >= y_min + 0.20 * H_mask) & (left_profile[:, 1] <= y_min + 0.75 * H_mask)
    mid_mask_R = (right_profile[:, 1] >= y_min + 0.20 * H_mask) & (right_profile[:, 1] <= y_min + 0.75 * H_mask)
    
    poly_L = np.polyfit(left_profile[mid_mask_L, 1], left_profile[mid_mask_L, 0], deg=1)
    poly_R = np.polyfit(right_profile[mid_mask_R, 1], right_profile[mid_mask_R, 0], deg=1)
    
    # 3. Exact Corner Endpoints Detection:
    # A corner is the point where the contour transitions from the lateral vertical line to the top/bottom curve.
    # We look for the deviation of the contour from the fitted lateral line (residual > threshold) or curvature peak.
    
    # Top-Left: search in upper 40% of left profile
    top_left_cand = left_profile[left_profile[:, 1] <= y_min + 0.40 * H_mask]
    # The top-left corner is where left_profile starts, or where horizontal derivative dx/dy sharply increases
    P_TL = top_left_cand[np.argmin(top_left_cand[:, 1])] # highest point on left edge
    
    # Top-Right: search in upper 40% of right profile
    top_right_cand = right_profile[right_profile[:, 1] <= y_min + 0.40 * H_mask]
    P_TR = top_right_cand[np.argmin(top_right_cand[:, 1])] # highest point on right edge
    
    # Bottom-Left: search where width starts narrowing sharply or where left profile deviates inward from poly_L
    bot_left_cand = left_profile[left_profile[:, 1] >= y_min + 0.60 * H_mask]
    # compute distance of bot_left_cand from poly_L line
    expected_x_L = poly_L[0] * bot_left_cand[:, 1] + poly_L[1]
    dist_L = bot_left_cand[:, 0] - expected_x_L
    # Inflection: the last point where dist_L is close to 0 (< 6 px), before the curve arches inward/downward
    valid_L = np.where(dist_L <= 8.0)[0]
    if len(valid_L) > 0:
        P_BL = bot_left_cand[valid_L[-1]]
    else:
        P_BL = bot_left_cand[np.argmax(bot_left_cand[:, 1])]
        
    # Bottom-Right: search where right profile deviates inward from poly_R
    bot_right_cand = right_profile[right_profile[:, 1] >= y_min + 0.60 * H_mask]
    expected_x_R = poly_R[0] * bot_right_cand[:, 1] + poly_R[1]
    dist_R = expected_x_R - bot_right_cand[:, 0]
    valid_R = np.where(dist_R <= 8.0)[0]
    if len(valid_R) > 0:
        P_BR = bot_right_cand[valid_R[-1]]
    else:
        P_BR = bot_right_cand[np.argmax(bot_right_cand[:, 1])]
        
    # 4. Extract continuous Top Curve T(u) and Bottom Curve B(u) directly from mask contour
    # Find indices of corners on the contour pts
    def find_nearest_contour_idx(pt, cnt_pts):
        dists = np.hypot(cnt_pts[:, 0] - pt[0], cnt_pts[:, 1] - pt[1])
        return int(np.argmin(dists))
        
    idx_TL = find_nearest_contour_idx(P_TL, pts)
    idx_TR = find_nearest_contour_idx(P_TR, pts)
    idx_BL = find_nearest_contour_idx(P_BL, pts)
    idx_BR = find_nearest_contour_idx(P_BR, pts)
    
    # Traverse contour between TL and TR for Top Curve
    # Contour points are ordered clockwise or counter-clockwise
    N_cnt = len(pts)
    if (idx_TR - idx_TL) % N_cnt < (idx_TL - idx_TR) % N_cnt:
        top_indices = [(idx_TL + i) % N_cnt for i in range((idx_TR - idx_TL) % N_cnt + 1)]
    else:
        top_indices = [(idx_TL - i) % N_cnt for i in range((idx_TL - idx_TR) % N_cnt + 1)]
    T_curve_pts = pts[top_indices]
    
    # Traverse contour between BL and BR for Bottom Curve
    if (idx_BR - idx_BL) % N_cnt < (idx_BL - idx_BR) % N_cnt:
        bot_indices = [(idx_BL + i) % N_cnt for i in range((idx_BR - idx_BL) % N_cnt + 1)]
    else:
        bot_indices = [(idx_BL - i) % N_cnt for i in range((idx_BL - idx_BR) % N_cnt + 1)]
    B_curve_pts = pts[bot_indices]
    
    # Sort T_curve_pts by x (left to right)
    if T_curve_pts[0, 0] > T_curve_pts[-1, 0]:
        T_curve_pts = T_curve_pts[::-1]
    if B_curve_pts[0, 0] > B_curve_pts[-1, 0]:
        B_curve_pts = B_curve_pts[::-1]
        
    # Resample curves smoothly to N_pts
    N_resample = 60
    u_vals = np.linspace(0.0, 1.0, N_resample)
    
    idx_T = np.linspace(0.0, 1.0, len(T_curve_pts))
    T_resampled = np.column_stack((
        np.interp(u_vals, idx_T, T_curve_pts[:, 0]),
        np.interp(u_vals, idx_T, T_curve_pts[:, 1])
    ))
    
    idx_B = np.linspace(0.0, 1.0, len(B_curve_pts))
    B_resampled = np.column_stack((
        np.interp(u_vals, idx_B, B_curve_pts[:, 0]),
        np.interp(u_vals, idx_B, B_curve_pts[:, 1])
    ))
    
    # Lateral lines as straight vectors
    v_vals = np.linspace(0.0, 1.0, N_resample)
    L_line = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
    R_line = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR
    
    return {
        "P_TL": P_TL,
        "P_TR": P_TR,
        "P_BL": P_BL,
        "P_BR": P_BR,
        "poly_L": poly_L,
        "poly_R": poly_R,
        "T_curve": T_resampled,
        "B_curve": B_resampled,
        "L_line": L_line,
        "R_line": R_line,
        "contour": pts
    }

# Test on both bottles and generate detailed before/after comparison
from pipeline.stage3_optimization import Stage3CylinderOptimizer
from pipeline.stage4_remapping import Stage4Remapper
from pipeline.stage5_ocr import Stage5OCRDecoder

remapper = Stage4Remapper()
ocr = Stage5OCRDecoder(use_gpu=True)
optimizer = Stage3CylinderOptimizer(grid_rows=24, grid_cols=32)

for prefix, crop, mask, title in [
    ("white_exact", img[240:860, 460:960], mask_white[240:860, 460:960], "Castillo de Liria (White)"),
    ("red_exact", img[250:850, 0:470], mask_red[250:850, 0:470], "Castillo de Liria (Red)")
]:
    geo = find_exact_corners_robust(mask)
    P_TL = geo["P_TL"]
    P_TR = geo["P_TR"]
    P_BL = geo["P_BL"]
    P_BR = geo["P_BR"]
    T_curve = geo["T_curve"]
    B_curve = geo["B_curve"]
    L_line = geo["L_line"]
    R_line = geo["R_line"]
    
    print(f"\n[{title}] Exact Corner Results:")
    print(f"  P_TL: {P_TL.round(1)} | P_TR: {P_TR.round(1)}")
    print(f"  P_BL: {P_BL.round(1)} | P_BR: {P_BR.round(1)}")
    
    # 1. Overlay of corners, lateral lines, and exact curves
    vis = crop.copy()
    
    # Lateral lines
    cv2.polylines(vis, [L_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [R_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
    
    # Top and Bottom exact curves from contour
    cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    
    # 4 Corner Points with precise crosshairs
    for pt, name in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
        px, py = int(pt[0]), int(pt[1])
        cv2.circle(vis, (px, py), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (px, py), 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (px, py), 2, (255, 255, 255), -1, cv2.LINE_AA)
        # crosshair
        cv2.line(vis, (px - 14, py), (px + 14, py), (0, 255, 255), 2, cv2.LINE_AA)
        cv2.line(vis, (px, py - 14), (px, py + 14), (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(vis, name, (px + 12, py - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)
        
    # 2. 3D Deformation Mesh
    boundaries_dict = {
        "P_TL": P_TL, "P_TR": P_TR, "P_BL": P_BL, "P_BR": P_BR,
        "T_curve_xs": T_curve[:, 0], "T_curve_ys": T_curve[:, 1],
        "B_curve_xs": B_curve[:, 0], "B_curve_ys": B_curve[:, 1],
        "L_curve": L_line, "R_curve": R_line
    }
    res_s3 = optimizer.process(
        img_bgr=crop,
        text_lines=[],
        line_segments=[],
        cam_info={},
        mask=mask,
        label_boundaries=boundaries_dict
    )
    vis_mesh = res_s3["vis_mesh"]
    
    # 3. Dewarping and OCR
    res_s4 = remapper.process(crop, res_s3)
    dewarped = res_s4["dewarped_bgr"]
    ocr_res = ocr.process(dewarped)
    
    print(f"  OCR Result: {ocr_res['full_text']}")
    
    cv2.imwrite(os.path.join(artifacts_dir, f"{prefix}_exact_corners.png"), vis)
    cv2.imwrite(os.path.join(artifacts_dir, f"{prefix}_exact_mesh.png"), vis_mesh)
    cv2.imwrite(os.path.join(artifacts_dir, f"{prefix}_exact_dewarped.png"), dewarped)
    cv2.imwrite(os.path.join(artifacts_dir, f"{prefix}_exact_ocr.png"), ocr_res["annotated_bgr"])

print("\nExact corner testing complete!")
