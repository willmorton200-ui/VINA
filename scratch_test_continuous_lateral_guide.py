import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

def find_continuous_lateral_corners(cnt, H_mask, W_mask, x_min, x_max, y_min, y_max):
    """
    Finds the true lowest corners P_BL and P_BR by tracing the continuous collinear
    generator line down through all interruptions, ribbons, and steps.
    """
    ys = cnt[:, 1]
    xs = cnt[:, 0]
    x_mid = (x_min + x_max) / 2.0
    
    unique_ys = np.sort(np.unique(ys))
    left_profile = []
    right_profile = []
    for y_cur in unique_ys:
        xs_at_y = cnt[cnt[:, 1] == y_cur, 0]
        left_profile.append([float(np.min(xs_at_y)), float(y_cur)])
        right_profile.append([float(np.max(xs_at_y)), float(y_cur)])
    left_profile = np.array(left_profile)
    right_profile = np.array(right_profile)
    
    # 1. Fit robust dominant generator line on upper-middle section (20% to 70% of height)
    mid_L = (left_profile[:, 1] >= y_min + 0.20 * H_mask) & (left_profile[:, 1] <= y_min + 0.70 * H_mask)
    mid_R = (right_profile[:, 1] >= y_min + 0.20 * H_mask) & (right_profile[:, 1] <= y_min + 0.70 * H_mask)
    
    poly_L = np.polyfit(left_profile[mid_L, 1], left_profile[mid_L, 0], deg=1)
    poly_R = np.polyfit(right_profile[mid_R, 1], right_profile[mid_R, 0], deg=1)
    
    # 2. Trace Left Generator from top to bottom
    # Tolerance for belonging to the same collinear line
    tol_L = max(5.0, 0.03 * W_mask)
    dist_L = np.abs(left_profile[:, 0] - np.polyval(poly_L, left_profile[:, 1]))
    
    # Inliers in the upper 40% -> P_TL is the uppermost inlier
    inliers_tl = left_profile[(left_profile[:, 1] <= y_min + 0.35 * H_mask) & (dist_L <= tol_L)]
    P_TL = inliers_tl[np.argmin(inliers_tl[:, 1])] if len(inliers_tl) > 0 else left_profile[0]
    
    # Inliers in bottom 50% -> P_BL is the LOWEST inlier before permanent inward departure
    # We search from bottom upwards or find max Y where point is still on the line
    cand_bl = left_profile[(left_profile[:, 1] >= y_min + 0.60 * H_mask) & (dist_L <= tol_L)]
    P_BL = cand_bl[np.argmax(cand_bl[:, 1])] if len(cand_bl) > 0 else left_profile[-1]
    
    # 3. Trace Right Generator from top to bottom
    tol_R = max(5.0, 0.03 * W_mask)
    dist_R = np.abs(right_profile[:, 0] - np.polyval(poly_R, right_profile[:, 1]))
    
    inliers_tr = right_profile[(right_profile[:, 1] <= y_min + 0.35 * H_mask) & (dist_R <= tol_R)]
    P_TR = inliers_tr[np.argmin(inliers_tr[:, 1])] if len(inliers_tr) > 0 else right_profile[0]
    
    cand_br = right_profile[(right_profile[:, 1] >= y_min + 0.60 * H_mask) & (dist_R <= tol_R)]
    P_BR = cand_br[np.argmax(cand_br[:, 1])] if len(cand_br) > 0 else right_profile[-1]
    
    return P_TL, P_TR, P_BL, P_BR, poly_L, poly_R

# Test specifically on Castillo White
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

P_TL, P_TR, P_BL, P_BR, poly_L, poly_R = find_continuous_lateral_corners(cnt, H_mask, W_mask, x_min, x_max, y_min, y_max)

print("Castillo White Continuous Corners:")
print("  P_TL:", P_TL)
print("  P_TR:", P_TR)
print("  P_BL:", P_BL)
print("  P_BR (True lowest corner near Cont. Net):", P_BR)
