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

# Defective mask (for honest demonstration of the bug)
defective_mask = cv2.imread('scratch_debug/barakiani_raw_mask.png', cv2.IMREAD_GRAYSCALE)
if defective_mask.shape[:2] != clean_mask.shape[:2]:
    defective_mask = cv2.resize(defective_mask, (clean_mask.shape[1], clean_mask.shape[0]))

h_vis = 600
w_vis = int(round(clean_mask.shape[1] * (h_vis / float(clean_mask.shape[0]))))

vis_defective = cv2.resize(cv2.cvtColor(defective_mask, cv2.COLOR_GRAY2BGR), (w_vis, h_vis))
vis_clean = cv2.resize(cv2.cvtColor(clean_mask, cv2.COLOR_GRAY2BGR), (w_vis, h_vis))

def draw_banner(im, text, color):
    b = np.zeros((50, im.shape[1], 3), dtype=np.uint8) + 25
    img_rgb = cv2.cvtColor(b, cv2.COLOR_BGR2RGB)
    pil_im = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_im)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 16)
    draw.text((12, 12), text, font=font, fill=color)
    res_b = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
    return np.vstack((res_b, im))

c1 = draw_banner(vis_defective, "ДЕФЕКТ: Порог Otsu выел узоры и низ", (255, 100, 100))
c2 = draw_banner(vis_clean, "ИСПРАВЛЕНО: Сплошная маска без дыр", (100, 255, 100))

pair = np.hstack((c1, c2))
hdr = np.zeros((55, pair.shape[1], 3), dtype=np.uint8) + 18
img_rgb = cv2.cvtColor(hdr, cv2.COLOR_BGR2RGB)
pil_hdr = PILImage.fromarray(img_rgb)
draw = ImageDraw.Draw(pil_hdr)
font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)
draw.text((20, 14), "Анализ дефекта маски: Исправление порога бумаги", font=font, fill=(255, 255, 255))
final_card = np.vstack((cv2.cvtColor(np.array(pil_hdr), cv2.COLOR_RGB2BGR), pair))

out_path = os.path.join(artifacts_dir, "barakiani_mask_bug_fix_explained.png")
cv2.imwrite(out_path, final_card)
print("Saved corrected explanation comparison:", out_path)
