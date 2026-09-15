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
from pipeline.vectorizer import MaskVectorizer

p1 = Stage1Preprocessor(use_gpu=True)
v = MaskVectorizer()

mask_full, _ = p1.sam_refiner.refine_mask(img, [479, 263, 960, 840])
crop_bgr = img[240:860, 460:960].copy()
mask_crop = mask_full[240:860, 460:960].copy()
h, w = crop_bgr.shape[:2]

vec = v.vectorize(mask_crop)
P_TL, P_TR, P_BL, P_BR = vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR

# Full view visualization
vis_full = crop_bgr.copy()
cv2.polylines(vis_full, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_full, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_full, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_full, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt, lbl in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, f"P_BR [{int(P_BR[0])},{int(P_BR[1])}]")]:
    px, py = int(pt[0]), int(pt[1])
    cv2.circle(vis_full, (px, py), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_full, (px, py), 6, (0, 0, 255), -1, cv2.LINE_AA)
    vis_full = draw_cyrillic(vis_full, lbl, (px - 140 if "P_BR" in lbl else px + 8, py - 8), font_size=15, text_color=(0, 255, 255), bg_color=(20, 20, 20))

# Zoom-in on bottom right corner (y from 360 to 570, x from 280 to 450)
zoom_crop = vis_full[350:570, 280:440].copy()
zoom_h, zoom_w = zoom_crop.shape[:2]
zoom_scaled = cv2.resize(zoom_crop, (int(zoom_w * 2.5), int(zoom_h * 2.5)), interpolation=cv2.INTER_LANCZOS4)

# Build presentation card
h_card = 550
w_full = int(round(vis_full.shape[1] * (h_card / float(vis_full.shape[0]))))
vis_full_scaled = cv2.resize(vis_full, (w_full, h_card), interpolation=cv2.INTER_LANCZOS4)

w_zoom = int(round(zoom_scaled.shape[1] * (h_card / float(zoom_scaled.shape[0]))))
zoom_final = cv2.resize(zoom_scaled, (w_zoom, h_card), interpolation=cv2.INTER_LANCZOS4)

b1 = np.zeros((45, w_full, 3), dtype=np.uint8) + 28
b1 = draw_cyrillic(b1, "Общий вид: Castillo Sauvignon Blanc", (10, 12), font_size=15, text_color=(0, 255, 255))
c1 = np.vstack((b1, vis_full_scaled))

b2 = np.zeros((45, w_zoom, 3), dtype=np.uint8) + 28
b2 = draw_cyrillic(b2, "Zoom: Высокоточная точка P_BR [387, 530]", (10, 12), font_size=15, text_color=(0, 255, 0))
c2 = np.vstack((b2, zoom_final))

row = np.hstack((c1, c2))
hdr = np.zeros((55, row.shape[1], 3), dtype=np.uint8) + 18
hdr = draw_cyrillic(hdr, "Высокоточное определение точки окончания образующей (порог угла 14°)", (20, 14), font_size=20, text_color=(255, 255, 255))
final_board = np.vstack((hdr, row))

out_path = os.path.join(artifacts_dir, "high_precision_p_br_zoom_board.png")
cv2.imwrite(out_path, final_board)
print(f"High precision zoom board saved: {out_path}")
