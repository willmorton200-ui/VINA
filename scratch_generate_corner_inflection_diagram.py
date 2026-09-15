import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

def draw_cyrillic(img_bgr, text, org, font_size=18, text_color=(255, 255, 255), bg_color=None):
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

from scratch_test_corner_angle_inflection import find_corner_by_min_internal_angle
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

cases = [
    {
        "id": "castillo_red",
        "title": "Castillo de Liria (Красная)",
        "img_path": "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg",
        "box": [0, 273, 463, 832],
        "crop": [0, 250, 470, 850]
    },
    {
        "id": "castillo_white",
        "title": "Castillo de Liria (Белая)",
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

rendered_cards = []

for c in cases:
    img = cv2.imread(c["img_path"])
    cx1, cy1, cx2, cy2 = c["crop"]
    crop_bgr = img[cy1:cy2, cx1:cx2].copy()
    h, w = crop_bgr.shape[:2]
    
    mask_full, _ = p1.sam_refiner.refine_mask(img, c["box"])
    mask_crop = mask_full[cy1:cy2, cx1:cx2].copy()
    
    binary = np.uint8(mask_crop > 127) * 255
    cnts, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(cnts, key=cv2.contourArea).squeeze(1)
    N_cnt = len(cnt)
    
    P_TL, P_TR, P_BL, P_BR, angles = find_corner_by_min_internal_angle(cnt, k=15)
    
    def find_idx(pt):
        return int(np.argmin(np.hypot(cnt[:, 0] - pt[0], cnt[:, 1] - pt[1])))
        
    i_tl, i_tr, i_bl, i_br = find_idx(P_TL), find_idx(P_TR), find_idx(P_BL), find_idx(P_BR)
    
    def get_seg(s_idx, e_idx):
        if (e_idx - s_idx) % N_cnt < (s_idx - e_idx) % N_cnt:
            return cnt[[(s_idx + i) % N_cnt for i in range((e_idx - s_idx) % N_cnt + 1)]]
        else:
            return cnt[[(s_idx - i) % N_cnt for i in range((s_idx - e_idx) % N_cnt + 1)]]

    T_seg = get_seg(i_tl, i_tr)
    B_seg = get_seg(i_bl, i_br)
    L_seg = get_seg(i_tl, i_bl)
    R_seg = get_seg(i_tr, i_br)
    
    vis = crop_bgr.copy()
    
    # Lateral curves in CYAN / BLUE
    cv2.polylines(vis, [L_seg], False, (255, 180, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [R_seg], False, (255, 180, 0), 4, cv2.LINE_AA)
    
    # Top & Bottom curves in GREEN
    cv2.polylines(vis, [T_seg], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [B_seg], False, (0, 255, 0), 4, cv2.LINE_AA)
    
    # Draw tangent arrows at P_BL and P_BR to show the sharp corner angle
    # Tangent coming down lateral wall
    p_bl_prev = cnt[(i_bl - 20) % N_cnt]
    p_bl_next = cnt[(i_bl + 20) % N_cnt]
    
    # Draw Corners
    for pt, lbl, col in [
        (P_TL, "P_TL", (0, 255, 255)),
        (P_TR, "P_TR", (0, 255, 255)),
        (P_BL, "P_BL (Угол)", (0, 80, 255)),
        (P_BR, "P_BR (Угол)", (0, 80, 255))
    ]:
        px, py = int(pt[0]), int(pt[1])
        cv2.circle(vis, (px, py), 10, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (px, py), 7, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (px, py), 2, (255, 255, 255), -1, cv2.LINE_AA)
        vis = draw_cyrillic(vis, lbl, (px + 10, py - 10), font_size=15, text_color=col, bg_color=(20, 20, 20))
        
    # Scale for card
    h_card = 520
    w_card = int(round(vis.shape[1] * (h_card / float(vis.shape[0]))))
    vis_scaled = cv2.resize(vis, (w_card, h_card), interpolation=cv2.INTER_LANCZOS4)
    
    banner = np.zeros((45, w_card, 3), dtype=np.uint8) + 28
    banner = draw_cyrillic(banner, c["title"], (10, 12), font_size=16, text_color=(0, 255, 255))
    card = np.vstack((banner, vis_scaled))
    card = cv2.copyMakeBorder(card, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=[60, 60, 60])
    rendered_cards.append(card)

row = np.hstack(rendered_cards)
hdr = np.zeros((60, row.shape[1], 3), dtype=np.uint8) + 18
hdr = draw_cyrillic(hdr, "Точки сопряжения P_BL и P_BR по минимальному внутреннему углу контура", (20, 16), font_size=22, text_color=(255, 255, 255))
final_board = np.vstack((hdr, row))

out_board = os.path.join(artifacts_dir, "corner_min_internal_angle_board.png")
cv2.imwrite(out_board, final_board)
print(f"Board saved: {out_board}")
