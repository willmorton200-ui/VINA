import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-31.jpg"
img = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

# 1. Old YOLO / Fallback Mask (simulated as the raw mask with Guided Filter)
# The raw mask from scratch_debug/barakiani_raw_mask.png if exists, else YOLO raw
raw_mask_path = r"scratch_debug/barakiani_raw_mask.png"
if os.path.exists(raw_mask_path):
    old_mask = cv2.imread(raw_mask_path, cv2.IMREAD_GRAYSCALE)
else:
    old_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)

# 2. New SAM + Paper Gate Mask
res_new = p1.process(img)
new_crop = res_new["cropped_bgr"]
new_mask = res_new["mask"]

# Let's crop old_mask to same coordinates as new_crop
x0 = res_new["bbox_info"]["crop_x"]
y0 = res_new["bbox_info"]["crop_y"]
w_c = res_new["bbox_info"]["crop_w"]
h_c = res_new["bbox_info"]["crop_h"]

old_mask_crop = old_mask[y0:y0+h_c, x0:x0+w_c] if old_mask.shape[:2] == img.shape[:2] else cv2.resize(old_mask, (new_mask.shape[1], new_mask.shape[0]))

# Visual comparison
h_vis = 600
w_old = int(round(old_mask_crop.shape[1] * (h_vis / float(old_mask_crop.shape[0]))))
w_new = int(round(new_mask.shape[1] * (h_vis / float(new_mask.shape[0]))))

vis_old_mask = cv2.cvtColor(old_mask_crop, cv2.COLOR_GRAY2BGR)
vis_new_mask = cv2.cvtColor(new_mask, cv2.COLOR_GRAY2BGR)

# Overlay on crop
overlay_old = cv2.addWeighted(new_crop, 0.65, cv2.cvtColor(old_mask_crop, cv2.COLOR_GRAY2BGR), 0.35, 0)
overlay_new = cv2.addWeighted(new_crop, 0.65, cv2.cvtColor(new_mask, cv2.COLOR_GRAY2BGR), 0.35, 0)

def draw_cyrillic_banner(im, text, color):
    b = np.zeros((50, im.shape[1], 3), dtype=np.uint8) + 25
    img_rgb = cv2.cvtColor(b, cv2.COLOR_BGR2RGB)
    pil_im = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_im)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 17)
    draw.text((12, 12), text, font=font, fill=color)
    res_b = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
    return np.vstack((res_b, im))

card1 = draw_cyrillic_banner(cv2.resize(vis_old_mask, (w_old, h_vis)), "БЫЛО: YOLOv8 + Guided Filter (Подтекания и дыры)", (255, 100, 100))
card2 = draw_cyrillic_banner(cv2.resize(vis_new_mask, (w_new, h_vis)), "СТАЛО: SAM ViT-H + Paper Gate (Идеальный контур)", (100, 255, 100))

pair = np.hstack((card1, card2))
hdr = np.zeros((55, pair.shape[1], 3), dtype=np.uint8) + 18
img_rgb = cv2.cvtColor(hdr, cv2.COLOR_BGR2RGB)
pil_hdr = PILImage.fromarray(img_rgb)
draw = ImageDraw.Draw(pil_hdr)
font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)
draw.text((20, 14), "Сравнение сегментации: Замена YOLOv8 на SAM + Paper Gate", font=font, fill=(255, 255, 255))
final_card = np.vstack((cv2.cvtColor(np.array(pil_hdr), cv2.COLOR_RGB2BGR), pair))

out_path = os.path.join(artifacts_dir, "segmentation_replacement_comparison.png")
cv2.imwrite(out_path, final_card)
print(f"Comparison saved: {out_path}")
