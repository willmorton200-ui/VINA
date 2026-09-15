import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

def find_corner_by_min_internal_angle(cnt, k=15):
    """
    Computes corner vertices as points with minimum internal angle 
    (maximum directional turning / sharpest inflection between lateral wall and curve).
    
    cnt: (N, 2) contour points in clockwise or counter-clockwise order
    k: step size for finite difference tangent vectors
    """
    N = len(cnt)
    ys = cnt[:, 1]
    xs = cnt[:, 0]
    
    y_min, y_max = np.min(ys), np.max(ys)
    x_min, x_max = np.min(xs), np.max(xs)
    H_mask = y_max - y_min
    W_mask = x_max - x_min
    x_mid = (x_min + x_max) / 2.0
    
    # Calculate internal angle at each contour vertex i
    # v_in: vector coming from p_{i-k} to p_i
    # v_out: vector going from p_i to p_{i+k}
    angles = np.zeros(N)
    cross_products = np.zeros(N)
    
    for i in range(N):
        p_prev = cnt[(i - k) % N]
        p_curr = cnt[i]
        p_next = cnt[(i + k) % N]
        
        v1 = p_curr - p_prev
        v2 = p_next - p_curr
        
        norm1 = np.hypot(v1[0], v1[1])
        norm2 = np.hypot(v2[0], v2[1])
        
        if norm1 < 1e-3 or norm2 < 1e-3:
            angles[i] = 180.0
            continue
            
        cos_ang = np.dot(v1, v2) / (norm1 * norm2)
        cos_ang = np.clip(cos_ang, -1.0, 1.0)
        # turning angle in degrees (0 = straight line, 90 = right angle turn)
        turn_angle = np.degrees(np.arccos(cos_ang))
        angles[i] = turn_angle
        
        # 2D cross product to detect convexity/turning direction
        cross_products[i] = v1[0] * v2[1] - v1[1] * v2[0]
        
    # --- SEARCH QUADRANTS FOR 4 CORNERS ---
    # 1. P_BL (Bottom-Left Corner):
    # Located in bottom 40% (Y in [y_min + 0.60*H, y_max]) and left half (X <= x_mid)
    # Must be at the sharpest turning corner where vertical lateral wall meets bottom curve
    cand_bl_idxs = np.where(
        (ys >= y_min + 0.60 * H_mask) & 
        (ys <= y_max - 0.02 * H_mask) & 
        (xs <= x_mid - 0.05 * W_mask)
    )[0]
    
    if len(cand_bl_idxs) > 0:
        # Sharpest turning angle = maximum turn_angle (minimum internal angle)
        # To avoid noise, also weight by distance from centroid/corner tendency
        best_bl_idx = cand_bl_idxs[np.argmax(angles[cand_bl_idxs])]
        P_BL = cnt[best_bl_idx]
    else:
        P_BL = cnt[np.argmin(xs)]
        
    # 2. P_BR (Bottom-Right Corner):
    # Located in bottom 40% (Y in [y_min + 0.60*H, y_max]) and right half (X >= x_mid)
    cand_br_idxs = np.where(
        (ys >= y_min + 0.60 * H_mask) & 
        (ys <= y_max - 0.02 * H_mask) & 
        (xs >= x_mid + 0.05 * W_mask)
    )[0]
    
    if len(cand_br_idxs) > 0:
        best_br_idx = cand_br_idxs[np.argmax(angles[cand_br_idxs])]
        P_BR = cnt[best_br_idx]
    else:
        P_BR = cnt[np.argmax(xs)]
        
    # 3. P_TL (Top-Left Corner):
    cand_tl_idxs = np.where(
        (ys <= y_min + 0.35 * H_mask) & 
        (xs <= x_mid - 0.05 * W_mask)
    )[0]
    if len(cand_tl_idxs) > 0:
        best_tl_idx = cand_tl_idxs[np.argmax(angles[cand_tl_idxs])]
        P_TL = cnt[best_tl_idx]
    else:
        P_TL = cnt[np.argmin(xs)]
        
    # 4. P_TR (Top-Right Corner):
    cand_tr_idxs = np.where(
        (ys <= y_min + 0.35 * H_mask) & 
        (xs >= x_mid + 0.05 * W_mask)
    )[0]
    if len(cand_tr_idxs) > 0:
        best_tr_idx = cand_tr_idxs[np.argmax(angles[cand_tr_idxs])]
        P_TR = cnt[best_tr_idx]
    else:
        P_TR = cnt[np.argmax(xs)]
        
    return P_TL, P_TR, P_BL, P_BR, angles

# Test on bottles
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

test_cases = [
    {
        "name": "Castillo_Red",
        "title": "Castillo de Liria Monastrell (Красная)",
        "img_path": "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg",
        "box": [0, 273, 463, 832],
        "crop": [0, 250, 470, 850]
    },
    {
        "name": "Castillo_White",
        "title": "Castillo de Liria Sauvignon (Белая)",
        "img_path": "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg",
        "box": [479, 263, 960, 840],
        "crop": [460, 240, 960, 860]
    },
    {
        "name": "Barakiani",
        "title": "BARAKIANI SAPERAVI",
        "img_path": "test_dataset/butilki/photo_2026-08-10_12-34-31.jpg",
        "box": [235, 360, 675, 1120],
        "crop": [220, 340, 700, 1150]
    }
]

def draw_cyrillic(img_bgr, text, org, font_size=18, text_color=(255, 255, 255)):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", font_size)
    draw.text(org, text, font=font, fill=text_color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

for tc in test_cases:
    print(f"\n--- Testing {tc['name']} ---")
    img = cv2.imread(tc["img_path"])
    cx1, cy1, cx2, cy2 = tc["crop"]
    crop_bgr = img[cy1:cy2, cx1:cx2].copy()
    
    mask_full, _ = p1.sam_refiner.refine_mask(img, tc["box"])
    mask_crop = mask_full[cy1:cy2, cx1:cx2].copy()
    
    # Retain largest component
    binary = np.uint8(mask_crop > 127) * 255
    cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(cnts, key=cv2.contourArea).squeeze(1)
    
    P_TL, P_TR, P_BL, P_BR, angles = find_corner_by_min_internal_angle(cnt, k=15)
    
    print(f"  P_TL: {P_TL}")
    print(f"  P_TR: {P_TR}")
    print(f"  P_BL (Угол сопряжения левой образующей и низа): {P_BL}")
    print(f"  P_BR (Угол сопряжения правой образующей и низа): {P_BR}")
    
    # Visualization
    vis = crop_bgr.copy()
    
    # Draw contour
    cv2.polylines(vis, [cnt], True, (200, 200, 200), 1, cv2.LINE_AA)
    
    # Draw 4 corners with sharp angle markers
    for pt, lbl, col in [
        (P_TL, "P_TL", (0, 255, 255)),
        (P_TR, "P_TR", (0, 255, 255)),
        (P_BL, "P_BL (Угол)", (0, 100, 255)),
        (P_BR, "P_BR (Угол)", (0, 100, 255))
    ]:
        px, py = int(pt[0]), int(pt[1])
        cv2.circle(vis, (px, py), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (px, py), 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (px, py), 3, (255, 255, 255), -1, cv2.LINE_AA)
        vis = draw_cyrillic(vis, f"{lbl}: [{px},{py}]", (px + 10, py - 10), font_size=15, text_color=col)
        
    out_vis_path = os.path.join(artifacts_dir, f"{tc['name']}_min_angle_corners.png")
    cv2.imwrite(out_vis_path, vis)
    print(f"  Saved visual: {out_vis_path}")

print("\nAll corner tests completed successfully!")
