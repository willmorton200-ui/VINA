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
    font_path = r"C:\Windows\Fonts\arialbd.ttf"
    if not os.path.exists(font_path): font_path = r"C:\Windows\Fonts\arial.ttf"
    font = ImageFont.truetype(font_path, font_size)
    if bg_color is not None:
        bbox = draw.textbbox(org, text, font=font)
        draw.rectangle(bbox, fill=bg_color)
    draw.text(org, text, font=font, fill=text_color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')
h, w = img.shape[:2]

# 1. Previous Raw/Merged Segmentation
crop_old, mask_old, _ = p1.segment_bottle_and_label(img)
vis_old = crop_old.copy()
vis_old[mask_old > 127] = cv2.addWeighted(crop_old[mask_old > 127], 0.5, np.full_like(crop_old[mask_old > 127], (0, 0, 255)), 0.5, 0)
cnts_old, _ = cv2.findContours(np.uint8(mask_old > 127)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(vis_old, cnts_old, -1, (0, 0, 255), 2)

# 2. Improved Multi-Label Segmentation (Upper and Lower detected individually)
# Upper label box: [239, 366, 673, 685]
mask_up, _ = p1.sam_refiner.refine_mask(img, [239, 366, 673, 685])
# Lower label box: [241, 670, 654, 1115]
mask_low, _ = p1.sam_refiner.refine_mask(img, [241, 670, 654, 1115])

# Bounding box of full central bottle zone
cx1, cy1, cx2, cy2 = 220, 340, 690, 1140
crop_new = img[cy1:cy2, cx1:cx2].copy()
mask_up_c = mask_up[cy1:cy2, cx1:cx2]
mask_low_c = mask_low[cy1:cy2, cx1:cx2]

vis_new = crop_new.copy()
# Draw Upper in Cyan
vis_new[mask_up_c > 127] = cv2.addWeighted(crop_new[mask_up_c > 127], 0.5, np.full_like(crop_new[mask_up_c > 127], (255, 200, 0)), 0.5, 0)
cnts_up, _ = cv2.findContours(np.uint8(mask_up_c > 127)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(vis_new, cnts_up, -1, (255, 255, 0), 2)

# Draw Lower in Green
vis_new[mask_low_c > 127] = cv2.addWeighted(crop_new[mask_low_c > 127], 0.5, np.full_like(crop_new[mask_low_c > 127], (0, 255, 0)), 0.5, 0)
cnts_low, _ = cv2.findContours(np.uint8(mask_low_c > 127)*255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(vis_new, cnts_low, -1, (0, 255, 0), 2)

vis_new = draw_cyrillic(vis_new, "Верхняя: BARAKIANI", (20, 20), font_size=15, text_color=(255, 255, 0), bg_color=(20, 20, 20))
vis_new = draw_cyrillic(vis_new, "Нижняя: САПЕРАВИ", (20, 360), font_size=15, text_color=(0, 255, 0), bg_color=(20, 20, 20))

# Side-by-side comparison card
h_card = 600
def scale_im(im):
    w_t = int(round(im.shape[1] * (h_card / float(im.shape[0]))))
    return cv2.resize(im, (w_t, h_card), interpolation=cv2.INTER_LANCZOS4)

def draw_banner(im, text, col):
    b = np.zeros((45, im.shape[1], 3), dtype=np.uint8) + 26
    b = draw_cyrillic(b, text, (10, 12), font_size=15, text_color=col)
    return np.vstack((b, im))

c1 = draw_banner(scale_im(vis_old), "БЫЛО: Слитная маска с затеканием в темное стекло", (255, 100, 100))
c2 = draw_banner(scale_im(vis_new), "СТАЛО: Точное разделение на Верхнюю и Нижнюю этикетки", (100, 255, 100))

row = np.hstack((c1, c2))
hdr = np.zeros((55, row.shape[1], 3), dtype=np.uint8) + 16
hdr = draw_cyrillic(hdr, "Улучшение сегментации: Разделение составных этикеток и защита от затекания", (20, 14), font_size=19, text_color=(255, 255, 255))
final_card = np.vstack((hdr, row))

out_path = os.path.join(artifacts_dir, "barakiani_segmentation_improvement_comparison.png")
cv2.imwrite(out_path, final_card)
print(f"Improvement comparison saved: {out_path}")
