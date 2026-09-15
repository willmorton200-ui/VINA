import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

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

# Load Castillo White
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-29.jpg')
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

mask_full, _ = p1.sam_refiner.refine_mask(img, [479, 263, 960, 840])
crop_bgr = img[240:860, 460:960].copy()
mask_crop = mask_full[240:860, 460:960].copy()
h, w = crop_bgr.shape[:2]

cnts, _ = cv2.findContours(np.uint8(mask_crop > 127)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(cnts, key=cv2.contourArea).squeeze(1)
N_cnt = len(cnt)

ys = cnt[:, 1]
xs = cnt[:, 0]
y_min, y_max = np.min(ys), np.max(ys)
x_min, x_max = np.min(xs), np.max(xs)
H_mask = y_max - y_min
W_mask = x_max - x_min

from scratch_test_continuous_lateral_guide import find_continuous_lateral_corners
P_TL, P_TR, P_BL, P_BR, poly_L, poly_R = find_continuous_lateral_corners(cnt, H_mask, W_mask, x_min, x_max, y_min, y_max)

# Old false P_BR at ribbon: [405, 445]
P_BR_old = np.array([405, 445])

def find_idx(pt):
    return int(np.argmin(np.hypot(cnt[:, 0] - pt[0], cnt[:, 1] - pt[1])))

# 1. Old visual (stopped at ribbon)
vis_old = crop_bgr.copy()
i_tl_o, i_tr_o, i_bl_o, i_br_o = find_idx(P_TL), find_idx(P_TR), find_idx(P_BL), find_idx(P_BR_old)
cv2.line(vis_old, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 160, 0), 4, cv2.LINE_AA)
cv2.line(vis_old, (int(P_TR[0]), int(P_TR[1])), (int(P_BR_old[0]), int(P_BR_old[1])), (255, 160, 0), 4, cv2.LINE_AA)
cv2.circle(vis_old, (int(P_BR_old[0]), int(P_BR_old[1])), 10, (0, 0, 255), -1, cv2.LINE_AA)
vis_old = draw_cyrillic(vis_old, "Ложный угол на ленте (y=445)", (int(P_BR_old[0]) - 240, int(P_BR_old[1]) - 10), font_size=15, text_color=(0, 0, 255), bg_color=(20, 20, 20))

# 2. New visual (continuous guide down to Cont. Net)
vis_new = crop_bgr.copy()
# Continuous right line from P_TR to true P_BR
v_pts = 60
v_vals = np.linspace(0.0, 1.0, v_pts)
L_line = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
R_line = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR

# Bottom curve from P_BL to P_BR
i_bl_n, i_br_n = find_idx(P_BL), find_idx(P_BR)
if (i_br_n - i_bl_n) % N_cnt < (i_bl_n - i_br_n) % N_cnt:
    B_seg = cnt[[(i_bl_n + i) % N_cnt for i in range((i_br_n - i_bl_n) % N_cnt + 1)]]
else:
    B_seg = cnt[[(i_bl_n - i) % N_cnt for i in range((i_bl_n - i_br_n) % N_cnt + 1)]]

cv2.polylines(vis_new, [L_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_new, [R_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_new, [B_seg], False, (0, 255, 0), 4, cv2.LINE_AA)

# Draw Corners
for pt, lbl, col in [
    (P_TL, "P_TL", (0, 255, 255)),
    (P_TR, "P_TR", (0, 255, 255)),
    (P_BL, "P_BL", (0, 255, 255)),
    (P_BR, "Истинный P_BR (y=547)", (0, 255, 0))
]:
    px, py = int(pt[0]), int(pt[1])
    cv2.circle(vis_new, (px, py), 10, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_new, (px, py), 7, (0, 0, 255) if "Ложный" in lbl else (0, 200, 0), -1, cv2.LINE_AA)
    vis_new = draw_cyrillic(vis_new, lbl, (px - 220 if "P_BR" in lbl else px + 10, py - 10), font_size=15, text_color=col, bg_color=(20, 20, 20))

# Side-by-side comparison card
h_card = 600
def scale_im(im):
    w_t = int(round(im.shape[1] * (h_card / float(im.shape[0]))))
    return cv2.resize(im, (w_t, h_card), interpolation=cv2.INTER_LANCZOS4)

def draw_banner(im, text, color):
    b = np.zeros((45, im.shape[1], 3), dtype=np.uint8) + 28
    b = draw_cyrillic(b, text, (10, 12), font_size=16, text_color=color)
    return np.vstack((b, im))

c1 = draw_banner(scale_im(vis_old), "БЫЛО: Остановка на выступе золотой ленты", (255, 100, 100))
c2 = draw_banner(scale_im(vis_new), "СТАЛО: Непрерывная направляющая сквозь ленту до низа", (100, 255, 100))

row = np.hstack((c1, c2))
hdr = np.zeros((55, row.shape[1], 3), dtype=np.uint8) + 18
hdr = draw_cyrillic(hdr, "Непрерывность боковой направляющей при прерываниях контура", (20, 14), font_size=21, text_color=(255, 255, 255))
final_card = np.vstack((hdr, row))

out_path = os.path.join(artifacts_dir, "lateral_guide_continuation_ribbon_fixed.png")
cv2.imwrite(out_path, final_card)
print(f"Comparison card saved: {out_path}")
