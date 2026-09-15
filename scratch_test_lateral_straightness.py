import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

def robust_straight_lateral_guide(raw_segment, P_top, P_bot, max_dev_px=6.0, N_pts=60):
    """
    Checks lateral contour for straightness (internal angle ~ 180 degrees),
    ignores sharp steps/notches in the middle, and fits a robust smooth generator line
    connecting P_top to P_bot.
    
    raw_segment: (M, 2) contour points between P_top and P_bot
    P_top: (2,) top corner
    P_bot: (2,) bottom corner
    """
    ys = raw_segment[:, 1]
    xs = raw_segment[:, 0]
    M = len(raw_segment)
    
    if M < 5:
        v_vals = np.linspace(0.0, 1.0, N_pts)
        return (1.0 - v_vals[:, None]) * P_top + v_vals[:, None] * P_bot
        
    # 1. Check local turning angles (flatness ~ 180 deg)
    k = max(2, min(5, M // 8))
    is_flat = np.ones(M, dtype=bool)
    
    for i in range(k, M - k):
        v1 = raw_segment[i] - raw_segment[i - k]
        v2 = raw_segment[i + k] - raw_segment[i]
        n1 = np.hypot(v1[0], v1[1])
        n2 = np.hypot(v2[0], v2[1])
        if n1 > 1e-3 and n2 > 1e-3:
            cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
            turn_deg = np.degrees(np.arccos(cos_a))
            # If turning angle > 25 deg (internal angle < 155 deg), it's a sharp step/notch
            if turn_deg > 25.0:
                is_flat[i] = False
                
    # 2. Fit straight generator line x = m*y + c through flat points
    flat_ys = ys[is_flat]
    flat_xs = xs[is_flat]
    
    if len(flat_ys) >= 6:
        # Linear regression with RANSAC-like tolerance
        poly = np.polyfit(flat_ys, flat_xs, deg=1)
        resids = np.abs(flat_xs - np.polyval(poly, flat_ys))
        inliers = resids <= max_dev_px
        if np.count_nonzero(inliers) >= 4:
            poly_refined = np.polyfit(flat_ys[inliers], flat_xs[inliers], deg=1)
        else:
            poly_refined = poly
    else:
        # Chord line connecting top to bottom
        dy = P_bot[1] - P_top[1]
        dx = P_bot[0] - P_top[0]
        m = dx / max(abs(dy), 1e-4)
        c = P_top[0] - m * P_top[1]
        poly_refined = np.array([m, c])
        
    # 3. Generate smooth lateral line strictly from P_top to P_bot
    v_vals = np.linspace(0.0, 1.0, N_pts)
    y_gen = (1.0 - v_vals) * P_top[1] + v_vals * P_bot[1]
    x_gen = np.polyval(poly_refined, y_gen)
    
    # Anchor perfectly to corner vertices
    x_gen[0] = P_top[0]
    x_gen[-1] = P_bot[0]
    
    return np.column_stack((x_gen, y_gen))

from scratch_test_corner_angle_inflection import find_corner_by_min_internal_angle
from pipeline.stage1_preprocessing import Stage1Preprocessor

p1 = Stage1Preprocessor(use_gpu=True)

test_cases = [
    {
        "id": "castillo_red",
        "title": "Castillo de Liria Monastrell (Красная)",
        "img_path": "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg",
        "box": [0, 273, 463, 832],
        "crop": [0, 250, 470, 850]
    },
    {
        "id": "castillo_white",
        "title": "Castillo de Liria Sauvignon (Белая)",
        "img_path": "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg",
        "box": [479, 263, 960, 840],
        "crop": [460, 240, 960, 860]
    },
    {
        "id": "barakiani",
        "title": "BARAKIANI (Саперави)",
        "img_path": "test_dataset/butilki/photo_2026-08-10_12-34-31.jpg",
        "box": [235, 360, 675, 1120],
        "crop": [220, 340, 700, 1150]
    }
]

def draw_cyrillic(img_bgr, text, org, font_size=16, text_color=(255, 255, 255), bg_color=None):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", font_size)
    if bg_color is not None:
        bbox = draw.textbbox(org, text, font=font)
        draw.rectangle(bbox, fill=bg_color)
    draw.text(org, text, font=font, fill=text_color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

cards = []

for tc in test_cases:
    img = cv2.imread(tc["img_path"])
    cx1, cy1, cx2, cy2 = tc["crop"]
    crop_bgr = img[cy1:cy2, cx1:cx2].copy()
    h, w = crop_bgr.shape[:2]
    
    mask_full, _ = p1.sam_refiner.refine_mask(img, tc["box"])
    mask_crop = mask_full[cy1:cy2, cx1:cx2].copy()
    
    binary = np.uint8(mask_crop > 127) * 255
    cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(cnts, key=cv2.contourArea).squeeze(1)
    N_cnt = len(cnt)
    
    # 1. 4 exact physical corners by minimum internal angle
    P_TL, P_TR, P_BL, P_BR, _ = find_corner_by_min_internal_angle(cnt, k=15)
    
    def find_idx(pt):
        return int(np.argmin(np.hypot(cnt[:, 0] - pt[0], cnt[:, 1] - pt[1])))
        
    i_tl, i_tr, i_bl, i_br = find_idx(P_TL), find_idx(P_TR), find_idx(P_BL), find_idx(P_BR)
    
    def get_seg(s_idx, e_idx):
        if (e_idx - s_idx) % N_cnt < (s_idx - e_idx) % N_cnt:
            return cnt[[(s_idx + i) % N_cnt for i in range((e_idx - s_idx) % N_cnt + 1)]]
        else:
            return cnt[[(s_idx - i) % N_cnt for i in range((s_idx - e_idx) % N_cnt + 1)]]

    raw_L = get_seg(i_tl, i_bl)
    raw_R = get_seg(i_tr, i_br)
    T_seg = get_seg(i_tl, i_tr)
    B_seg = get_seg(i_bl, i_br)
    
    # 2. Check lateral straightness at angles ~ 180 deg & ignore middle steps
    clean_L = robust_straight_lateral_guide(raw_L, P_TL, P_BL)
    clean_R = robust_straight_lateral_guide(raw_R, P_TR, P_BR)
    
    vis = crop_bgr.copy()
    
    # Draw raw contour in faint grey to show where notches/steps existed
    cv2.polylines(vis, [raw_L], False, (80, 80, 80), 2, cv2.LINE_AA)
    cv2.polylines(vis, [raw_R], False, (80, 80, 80), 2, cv2.LINE_AA)
    
    # Draw smooth straight lateral guides in bright blue
    cv2.polylines(vis, [clean_L.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [clean_R.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
    
    # Draw top & bottom curves in bright green
    cv2.polylines(vis, [T_seg], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [B_seg], False, (0, 255, 0), 4, cv2.LINE_AA)
    
    # Draw 4 corner points
    for pt, lbl in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
        px, py = int(pt[0]), int(pt[1])
        cv2.circle(vis, (px, py), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (px, py), 6, (0, 0, 255), -1, cv2.LINE_AA)
        vis = draw_cyrillic(vis, lbl, (px + 8, py - 8), font_size=15, text_color=(0, 255, 255), bg_color=(20, 20, 20))
        
    h_card = 520
    w_card = int(round(vis.shape[1] * (h_card / float(vis.shape[0]))))
    vis_scaled = cv2.resize(vis, (w_card, h_card), interpolation=cv2.INTER_LANCZOS4)
    
    b = np.zeros((45, w_card, 3), dtype=np.uint8) + 28
    b = draw_cyrillic(b, tc["title"], (10, 12), font_size=15, text_color=(0, 255, 255))
    card = np.vstack((b, vis_scaled))
    card = cv2.copyMakeBorder(card, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=[60, 60, 60])
    cards.append(card)

row = np.hstack(cards)
hdr = np.zeros((60, row.shape[1], 3), dtype=np.uint8) + 18
hdr = draw_cyrillic(hdr, "Проверка боковых образующих на ровность (углы ~180°) и фильтрация ступеней", (20, 16), font_size=20, text_color=(255, 255, 255))
final_board = np.vstack((hdr, row))

out_path = os.path.join(artifacts_dir, "lateral_straightness_verified_board.png")
cv2.imwrite(out_path, final_board)
print(f"Verified board saved: {out_path}")

