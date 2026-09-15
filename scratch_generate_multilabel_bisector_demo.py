import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
font_dir = r"C:\Windows\Fonts"

def draw_cyrillic(img_bgr, text, org, font_size=16, text_color=(255, 255, 255), bg_color=None):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    font = ImageFont.truetype(os.path.join(font_dir, "arialbd.ttf"), font_size)
    if bg_color is not None:
        bbox = draw.textbbox(org, text, font=font)
        draw.rectangle(bbox, fill=bg_color)
    draw.text(org, text, font=font, fill=text_color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

from pipeline.multi_label_engine import MultiLabelBottleEngine
engine = MultiLabelBottleEngine(use_gpu=True)

# Run on Barakiani (photo_2026-08-10_12-34-31.jpg)
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')
bottles = engine.process_image(img)

# Main bottle
b = bottles[0]

# Generate multi-panel infographic
cards = []
for lbl in b.labels:
    crop_rot = lbl.crop_bgr.copy()
    vec = lbl.vector_mask
    
    # Draw guides and corners
    cv2.polylines(crop_rot, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
    cv2.polylines(crop_rot, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 4, cv2.LINE_AA)
    cv2.polylines(crop_rot, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(crop_rot, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    
    # Draw bisector line down the middle
    mid_top = (vec.P_TL + vec.P_TR) / 2.0
    mid_bot = (vec.P_BL + vec.P_BR) / 2.0
    cv2.line(crop_rot, (int(mid_top[0]), int(mid_top[1])), (int(mid_bot[0]), int(mid_bot[1])), (0, 255, 255), 2, cv2.LINE_AA)
    
    # Card 1: Rectified crop with bisector
    h_box = 450
    w_t = int(round(crop_rot.shape[1] * (h_box / float(crop_rot.shape[0]))))
    crop_s = cv2.resize(crop_rot, (w_t, h_box), interpolation=cv2.INTER_LANCZOS4)
    b1 = np.zeros((40, crop_s.shape[1], 3), dtype=np.uint8) + 26
    b1 = draw_cyrillic(b1, f"Кроп: {lbl.label_type} (Биссектриса 90.0°)", (8, 10), font_size=13, text_color=(0, 255, 255))
    panel1 = np.vstack((b1, crop_s))
    
    # Card 2: Dewarped scan + OCR
    dew_s = cv2.resize(lbl.dewarped_ocr["annotated_bgr"], (w_t, h_box), interpolation=cv2.INTER_LANCZOS4)
    b2 = np.zeros((40, dew_s.shape[1], 3), dtype=np.uint8) + 26
    b2 = draw_cyrillic(b2, f"Развертка: {lbl.transformation_status}", (8, 10), font_size=13, text_color=(100, 255, 100))
    panel2 = np.vstack((b2, dew_s))
    
    sub_row = np.hstack((panel1, panel2))
    cards.append(sub_row)

# Stack labels top to bottom
target_w = max(c.shape[1] for c in cards)
def pad_to_w(im):
    if im.shape[1] == target_w: return im
    diff = target_w - im.shape[1]
    return cv2.copyMakeBorder(im, 0, 0, 0, diff, cv2.BORDER_CONSTANT, value=[30, 30, 30])

c_up = pad_to_w(cards[0])
c_low = pad_to_w(cards[1])
sep = np.zeros((20, target_w, 3), dtype=np.uint8) + 45
sep = draw_cyrillic(sep, "Порядок этикеток одной бутылки: СВЕРХУ ВНИЗ (Top-to-Bottom Hierarchy)", (20, 3), font_size=12, text_color=(200, 200, 200))

full_board = np.vstack((c_up, sep, c_low))
hdr = np.zeros((55, target_w, 3), dtype=np.uint8) + 16
hdr = draw_cyrillic(hdr, f"Мульти-этикетка бутылки BARAKIANI | Статус: {b.overall_status} | Всего слов: {b.total_dewarped_words}", (18, 14), font_size=18, text_color=(255, 255, 255))
final_board = np.vstack((hdr, full_board))

out_path = os.path.join(artifacts_dir, "multilabel_bisector_verticalization_board.png")
cv2.imwrite(out_path, final_board)
print(f"Board saved to: {out_path}")
