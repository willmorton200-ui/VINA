import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)
res = p1.process(img)

clean_mask = res["mask"]
crop_bgr = res["cropped_bgr"]

h_vis = 600
w_vis = int(round(clean_mask.shape[1] * (h_vis / float(clean_mask.shape[0]))))

vis_crop = cv2.resize(crop_bgr, (w_vis, h_vis))
vis_mask = cv2.resize(cv2.cvtColor(clean_mask, cv2.COLOR_GRAY2BGR), (w_vis, h_vis))

# Overlay
mask_color = np.zeros_like(vis_crop)
mask_color[cv2.resize(clean_mask, (w_vis, h_vis)) > 127] = [0, 255, 0]
vis_overlay = cv2.addWeighted(vis_crop, 0.70, mask_color, 0.30, 0)
cnts, _ = cv2.findContours(cv2.resize(clean_mask, (w_vis, h_vis)), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(vis_overlay, cnts, -1, (0, 255, 255), 2)

def draw_banner(im, text, color):
    b = np.zeros((45, im.shape[1], 3), dtype=np.uint8) + 28
    img_rgb = cv2.cvtColor(b, cv2.COLOR_BGR2RGB)
    pil_im = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_im)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 15)
    draw.text((10, 12), text, font=font, fill=color)
    res_b = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
    return np.vstack((res_b, im))

c1 = draw_banner(vis_crop, "1. Исходный кроп бутылки", (255, 255, 255))
c2 = draw_banner(vis_mask, "2. Сплошная маска (Дырки залиты)", (0, 255, 0))
c3 = draw_banner(vis_overlay, "3. Наложение (Без проливов наружу)", (0, 255, 255))

trio = np.hstack((c1, c2, c3))
hdr = np.zeros((55, trio.shape[1], 3), dtype=np.uint8) + 18
img_rgb = cv2.cvtColor(hdr, cv2.COLOR_BGR2RGB)
pil_hdr = PILImage.fromarray(img_rgb)
draw = ImageDraw.Draw(pil_hdr)
font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)
draw.text((20, 14), "VINA Stage 1: Заливка дыр + Строгое отсечение контура", font=font, fill=(255, 255, 255))
final_card = np.vstack((cv2.cvtColor(np.array(pil_hdr), cv2.COLOR_RGB2BGR), trio))

out_path = os.path.join(artifacts_dir, "barakiani_perfect_solid_mask_overlay.png")
cv2.imwrite(out_path, final_card)
print(f"Final solid card saved: {out_path}")
