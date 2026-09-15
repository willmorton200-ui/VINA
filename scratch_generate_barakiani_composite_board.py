import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"

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

b_up = cv2.imread(os.path.join(artifacts_dir, "barakiani_upper_label_dewarp_ocr_board.png"))
b_low = cv2.imread(os.path.join(artifacts_dir, "barakiani_lower_label_dewarp_ocr_board.png"))

# Scale to matching width
target_w = 1400
def scale_w(im):
    h_t = int(round(im.shape[0] * (target_w / float(im.shape[1]))))
    return cv2.resize(im, (target_w, h_t), interpolation=cv2.INTER_LANCZOS4)

b_up_s = scale_w(b_up)
b_low_s = scale_w(b_low)

divider = np.zeros((15, target_w, 3), dtype=np.uint8) + 40
composite = np.vstack((b_up_s, divider, b_low_s))

out_path = os.path.join(artifacts_dir, "barakiani_full_dewarp_and_ocr_board.png")
cv2.imwrite(out_path, composite)
print(f"Composite Barakiani board saved: {out_path}")
