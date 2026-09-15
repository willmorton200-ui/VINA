import cv2
import numpy as np
import os

def compute_internal_angles(cnt_pts, k=10):
    """
    Computes internal angle alpha(i) in degrees at each contour point i.
    alpha = 180 deg on straight/smooth lines.
    alpha = min (~70-95 deg) at physical corner vertices.
    """
    N = len(cnt_pts)
    internal_angles = np.zeros(N)
    
    for i in range(N):
        p_prev = cnt_pts[(i - k) % N]
        p_curr = cnt_pts[i]
        p_next = cnt_pts[(i + k) % N]
        
        v_in = p_curr - p_prev
        v_out = p_next - p_curr
        
        n_in = np.hypot(v_in[0], v_in[1])
        n_out = np.hypot(v_out[0], v_out[1])
        
        if n_in < 1e-3 or n_out < 1e-3:
            internal_angles[i] = 180.0
            continue
            
        # cos(turning_angle) = (v_in . v_out) / (|v_in| * |v_out|)
        cos_turn = np.clip(np.dot(v_in, v_out) / (n_in * n_out), -1.0, 1.0)
        turn_angle_deg = np.degrees(np.arccos(cos_turn))
        
        # Internal angle alpha = 180 - turning_angle
        internal_angles[i] = 180.0 - turn_angle_deg
        
    return internal_angles

def extract_universal_min_angle_corners(cnt, k_ratio=0.015):
    """
    Universal Rule for ALL labels:
    4 corners are the STRICT GLOBAL MINIMUM OF INTERNAL ANGLE in each of the 4 quadrants.
    """
    pts = cnt.squeeze(1) if len(cnt.shape) == 3 else cnt
    N = len(pts)
    
    k = max(5, int(N * k_ratio))
    angles = compute_internal_angles(pts, k=k)
    
    ys = pts[:, 1]
    xs = pts[:, 0]
    y_min, y_max = np.min(ys), np.max(ys)
    x_min, x_max = np.min(xs), np.max(xs)
    H = y_max - y_min
    W = x_max - x_min
    x_mid = (x_min + x_max) / 2.0
    
    # 1. P_BL: Minimum internal angle in Bottom-Left quadrant (y >= y_min + 0.50*H, x <= x_mid)
    cand_bl = np.where((ys >= y_min + 0.50 * H) & (xs <= x_mid))[0]
    i_bl = cand_bl[np.argmin(angles[cand_bl])] if len(cand_bl) > 0 else int(np.argmin(xs))
    P_BL = pts[i_bl]
    alpha_BL = angles[i_bl]
    
    # 2. P_BR: Minimum internal angle in Bottom-Right quadrant (y >= y_min + 0.50*H, x >= x_mid)
    cand_br = np.where((ys >= y_min + 0.50 * H) & (xs >= x_mid))[0]
    i_br = cand_br[np.argmin(angles[cand_br])] if len(cand_br) > 0 else int(np.argmax(xs))
    P_BR = pts[i_br]
    alpha_BR = angles[i_br]
    
    # 3. P_TL: Minimum internal angle in Top-Left quadrant (y <= y_min + 0.40*H, x <= x_mid)
    cand_tl = np.where((ys <= y_min + 0.40 * H) & (xs <= x_mid))[0]
    i_tl = cand_tl[np.argmin(angles[cand_tl])] if len(cand_tl) > 0 else int(np.argmin(xs))
    P_TL = pts[i_tl]
    alpha_TL = angles[i_tl]
    
    # 4. P_TR: Minimum internal angle in Top-Right quadrant (y <= y_min + 0.40*H, x >= x_mid)
    cand_tr = np.where((ys <= y_min + 0.40 * H) & (xs >= x_mid))[0]
    i_tr = cand_tr[np.argmin(angles[cand_tr])] if len(cand_tr) > 0 else int(np.argmax(xs))
    P_TR = pts[i_tr]
    alpha_TR = angles[i_tr]
    
    return {
        "P_TL": P_TL, "alpha_TL": alpha_TL,
        "P_TR": P_TR, "alpha_TR": alpha_TR,
        "P_BL": P_BL, "alpha_BL": alpha_BL,
        "P_BR": P_BR, "alpha_BR": alpha_BR,
        "angles": angles, "pts": pts
    }

# Test on all 3 bottles
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

test_bottles = [
    ("Castillo_White", "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg", [479, 263, 960, 840], [460, 240, 960, 860]),
    ("Castillo_Red", "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg", [0, 273, 463, 832], [0, 250, 470, 850]),
    ("Barakiani", "test_dataset/butilki/photo_2026-08-10_12-34-31.jpg", [235, 360, 675, 1120], [220, 340, 700, 1150])
]

for name, img_path, box, crop_box in test_bottles:
    img = cv2.imread(img_path)
    mask_full, _ = p1.sam_refiner.refine_mask(img, box)
    cx1, cy1, cx2, cy2 = crop_box
    mask_crop = mask_full[cy1:cy2, cx1:cx2]
    
    cnts, _ = cv2.findContours(np.uint8(mask_crop > 127)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(cnts, key=cv2.contourArea)
    
    res = extract_universal_min_angle_corners(cnt)
    print(f"\n--- {name} ---")
    print(f"  P_TL: {res['P_TL']} (угол alpha={res['alpha_TL']:.1f} deg)")
    print(f"  P_TR: {res['P_TR']} (угол alpha={res['alpha_TR']:.1f} deg)")
    print(f"  P_BL: {res['P_BL']} (угол alpha={res['alpha_BL']:.1f} deg)")
    print(f"  P_BR: {res['P_BR']} (угол alpha={res['alpha_BR']:.1f} deg)")
