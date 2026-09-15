import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

def find_high_precision_corners(cnt, H_mask, W_mask, x_min, x_max, y_min, y_max, angle_thresh_deg=14.0):
    """
    High-precision corner detector with reduced minimum transition angle threshold.
    Detects the exact point where the linear vertical generator transitions into the bottom/top curves.
    """
    ys = cnt[:, 1]
    xs = cnt[:, 0]
    N = len(cnt)
    
    unique_ys = np.sort(np.unique(ys))
    left_profile = []
    right_profile = []
    for y_cur in unique_ys:
        xs_at_y = cnt[cnt[:, 1] == y_cur, 0]
        left_profile.append([float(np.min(xs_at_y)), float(y_cur)])
        right_profile.append([float(np.max(xs_at_y)), float(y_cur)])
    left_profile = np.array(left_profile)
    right_profile = np.array(right_profile)
    
    # 1. Fit dominant linear wall generator on middle 30%-65% of height
    mid_L = (left_profile[:, 1] >= y_min + 0.25 * H_mask) & (left_profile[:, 1] <= y_min + 0.65 * H_mask)
    mid_R = (right_profile[:, 1] >= y_min + 0.25 * H_mask) & (right_profile[:, 1] <= y_min + 0.65 * H_mask)
    
    poly_L = np.polyfit(left_profile[mid_L, 1], left_profile[mid_L, 0], deg=1)
    poly_R = np.polyfit(right_profile[mid_R, 1], right_profile[mid_R, 0], deg=1)
    
    # Wall slope vectors (unit direction along the lateral wall)
    dir_wall_L = np.array([poly_L[0], 1.0])
    dir_wall_L /= np.hypot(dir_wall_L[0], dir_wall_L[1])
    
    dir_wall_R = np.array([poly_R[0], 1.0])
    dir_wall_R /= np.hypot(dir_wall_R[0], dir_wall_R[1])
    
    # 2. High-Precision P_BR: Trace right profile from middle downwards
    # Stop as soon as the contour vector deviates by > angle_thresh_deg from the wall generator
    cand_br_pts = right_profile[right_profile[:, 1] >= y_min + 0.50 * H_mask]
    best_br = cand_br_pts[0]
    
    # Use sliding window of 6 points to compute local tangent direction
    k_win = 6
    for i in range(len(cand_br_pts) - k_win):
        p1 = cand_br_pts[i]
        p2 = cand_br_pts[i + k_win]
        vec = p2 - p1
        norm_v = np.hypot(vec[0], vec[1])
        if norm_v < 1e-3:
            continue
        vec_norm = vec / norm_v
        
        # Angle deviation relative to the right wall generator
        cos_dev = np.clip(np.dot(vec_norm, dir_wall_R), -1.0, 1.0)
        dev_deg = np.degrees(np.arccos(cos_dev))
        
        # Also check distance from straight generator line
        dist_from_line = np.abs(p1[0] - np.polyval(poly_R, p1[1]))
        
        if dev_deg > angle_thresh_deg or dist_from_line > max(5.0, 0.025 * W_mask):
            # The corner is right at the departure point
            best_br = cand_br_pts[i]
            break
        else:
            best_br = cand_br_pts[i]
            
    P_BR = best_br
    
    # 3. High-Precision P_BL: Trace left profile from middle downwards
    cand_bl_pts = left_profile[left_profile[:, 1] >= y_min + 0.50 * H_mask]
    best_bl = cand_bl_pts[0]
    
    for i in range(len(cand_bl_pts) - k_win):
        p1 = cand_bl_pts[i]
        p2 = cand_bl_pts[i + k_win]
        vec = p2 - p1
        norm_v = np.hypot(vec[0], vec[1])
        if norm_v < 1e-3:
            continue
        vec_norm = vec / norm_v
        
        cos_dev = np.clip(np.dot(vec_norm, dir_wall_L), -1.0, 1.0)
        dev_deg = np.degrees(np.arccos(cos_dev))
        dist_from_line = np.abs(p1[0] - np.polyval(poly_L, p1[1]))
        
        if dev_deg > angle_thresh_deg or dist_from_line > max(5.0, 0.025 * W_mask):
            best_bl = cand_bl_pts[i]
            break
        else:
            best_bl = cand_bl_pts[i]
            
    P_BL = best_bl
    
    # 4. Top corners P_TL and P_TR (Uppermost inliers on generator)
    tol_L = max(4.0, 0.02 * W_mask)
    dist_L_top = np.abs(left_profile[:, 0] - np.polyval(poly_L, left_profile[:, 1]))
    inliers_tl = left_profile[(left_profile[:, 1] <= y_min + 0.35 * H_mask) & (dist_L_top <= tol_L)]
    P_TL = inliers_tl[np.argmin(inliers_tl[:, 1])] if len(inliers_tl) > 0 else left_profile[0]
    
    tol_R = max(4.0, 0.02 * W_mask)
    dist_R_top = np.abs(right_profile[:, 0] - np.polyval(poly_R, right_profile[:, 1]))
    inliers_tr = right_profile[(right_profile[:, 1] <= y_min + 0.35 * H_mask) & (dist_R_top <= tol_R)]
    P_TR = inliers_tr[np.argmin(inliers_tr[:, 1])] if len(inliers_tr) > 0 else right_profile[0]
    
    return P_TL, P_TR, P_BL, P_BR, poly_L, poly_R

# Test on Castillo White specifically
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-29.jpg')
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

mask_full, _ = p1.sam_refiner.refine_mask(img, [479, 263, 960, 840])
crop_bgr = img[240:860, 460:960].copy()
mask_crop = mask_full[240:860, 460:960].copy()

cnts, _ = cv2.findContours(np.uint8(mask_crop > 127)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(cnts, key=cv2.contourArea).squeeze(1)

ys = cnt[:, 1]
xs = cnt[:, 0]
y_min, y_max = np.min(ys), np.max(ys)
x_min, x_max = np.min(xs), np.max(xs)
H_mask = y_max - y_min
W_mask = x_max - x_min

P_TL, P_TR, P_BL, P_BR, poly_L, poly_R = find_high_precision_corners(cnt, H_mask, W_mask, x_min, x_max, y_min, y_max, angle_thresh_deg=14.0)

print("Castillo White High-Precision Corners (angle_thresh=14 deg):")
print("  P_TL:", P_TL)
print("  P_TR:", P_TR)
print("  P_BL:", P_BL)
print("  P_BR (Exact physical corner):", P_BR)
