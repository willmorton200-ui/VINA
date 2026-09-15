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

print(f"Castillo White High-Precision Corners:")
print(f"  P_TL: {P_TL}")
print(f"  P_TR: {P_TR}")
print(f"  P_BL (Левый угол у основания): {P_BL}")
print(f"  P_BR (Правый угол у основания): {P_BR}")

# Full visualization
vis = crop_bgr.copy()
cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt, lbl in [
    (P_TL, f"P_TL [{int(P_TL[0])},{int(P_TL[1])}]"),
    (P_TR, f"P_TR [{int(P_TR[0])},{int(P_TR[1])}]"),
    (P_BL, f"P_BL [{int(P_BL[0])},{int(P_BL[1])}]"),
    (P_BR, f"P_BR [{int(P_BR[0])},{int(P_BR[1])}]")
]:
    px, py = int(pt[0]), int(pt[1])
    cv2.circle(vis, (px, py), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (px, py), 6, (0, 0, 255), -1, cv2.LINE_AA)
    align_left = px > w // 2
    org_x = px - 160 if align_left else px + 8
    vis = draw_cyrillic(vis, lbl, (org_x, py - 8), font_size=15, text_color=(0, 255, 255), bg_color=(20, 20, 20))

# 1. Zoom Left Corner P_BL (y from 340 to 540, x from 0 to 180)
zoom_bl = vis[340:540, 0:180].copy()
zoom_bl_scaled = cv2.resize(zoom_bl, (int(zoom_bl.shape[1] * 2.5), int(zoom_bl.shape[0] * 2.5)), interpolation=cv2.INTER_LANCZOS4)

# 2. Zoom Right Corner P_BR (y from 360 to 570, x from 280 to 450)
zoom_br = vis[360:570, 280:450].copy()
zoom_br_scaled = cv2.resize(zoom_br, (int(zoom_br.shape[1] * 2.5), int(zoom_br.shape[0] * 2.5)), interpolation=cv2.INTER_LANCZOS4)

h_card = 520
def scale_to_h(im):
    w_t = int(round(im.shape[1] * (h_card / float(im.shape[0]))))
    return cv2.resize(im, (w_t, h_card), interpolation=cv2.INTER_LANCZOS4)

def draw_banner(im, text, color):
    b = np.zeros((45, im.shape[1], 3), dtype=np.uint8) + 28
    b = draw_cyrillic(b, text, (10, 12), font_size=15, text_color=color)
    return np.vstack((b, im))

c_full = draw_banner(scale_to_h(vis), "1. Общий вид этикетки", (255, 255, 255))
c_bl = draw_banner(scale_to_h(zoom_bl_scaled), f"2. Zoom P_BL [{int(P_BL[0])},{int(P_BL[1])}] сквозь ленту", (0, 255, 0))
c_br = draw_banner(scale_to_h(zoom_br_scaled), f"3. Zoom P_BR [{int(P_BR[0])},{int(P_BR[1])}] сквозь ленту", (0, 255, 0))

trio = np.hstack((c_full, c_bl, c_br))
hdr = np.zeros((55, trio.shape[1], 3), dtype=np.uint8) + 18
hdr = draw_cyrillic(hdr, "Сквозная трассировка обеих образующих P_BL и P_BR сквозь выступы ленты", (20, 14), font_size=20, text_color=(255, 255, 255))
final_board = np.vstack((hdr, trio))

out_path = os.path.join(artifacts_dir, "both_corners_continuous_zoom_board.png")
cv2.imwrite(out_path, final_board)
print(f"Board saved: {out_path}")
