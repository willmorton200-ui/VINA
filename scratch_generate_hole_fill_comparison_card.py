import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

# Raw SAM mask with both leaks and holes
prompt_box = [235, 360, 675, 1120]
mask_raw, _ = p1.sam_refiner.refine_mask(img, prompt_box)

crop_bgr = img[340:1150, 220:700].copy()
mask_crop = mask_raw[340:1150, 220:700].copy()
h, w = crop_bgr.shape[:2]

# Card 1: Raw mask with problems highlighted
# Convert to BGR black/white
vis_1 = np.zeros_like(crop_bgr)
vis_1[mask_crop > 127] = [255, 255, 255]

# Card 2: Leak detection & Boundary finding
lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
l_channel = lab[:, :, 0]
sobel_y = cv2.Sobel(l_channel, cv2.CV_64F, 0, 1, ksize=3)

# Bridge gap & fill
kernel_vert = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 25))
mask_bridged = cv2.morphologyEx(np.uint8(mask_crop > 127)*255, cv2.MORPH_CLOSE, kernel_vert)
cnts, _ = cv2.findContours(mask_bridged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
mask_filled = np.zeros_like(mask_crop)
if cnts:
    largest_cnt = max(cnts, key=cv2.contourArea)
    cv2.drawContours(mask_filled, [largest_cnt], -1, 255, -1)

top_pts = []
bot_pts = []
for x_col in range(w):
    col = np.where(mask_filled[:, x_col] > 127)[0]
    if len(col) < 30:
        continue
    y_s, y_e = col[0], col[-1]
    
    # Top gradient
    y_t_min, y_t_max = max(0, y_s - 15), min(h - 1, y_s + 40)
    top_grads = sobel_y[y_t_min:y_t_max, x_col]
    best_t = y_t_min + np.argmax(top_grads) if len(top_grads) > 0 else y_s
    top_pts.append((x_col, best_t))
    
    # Bottom gradient
    y_b_min, y_b_max = max(0, y_e - 60), min(h - 1, y_e + 20)
    bot_grads = sobel_y[y_b_min:y_b_max, x_col]
    best_b = y_b_min + np.argmin(bot_grads) if len(bot_grads) > 0 else y_e
    bot_pts.append((x_col, best_b))

top_pts = np.array(top_pts)
bot_pts = np.array(bot_pts)

poly_t = np.polyfit(top_pts[:, 0], top_pts[:, 1], deg=2)
poly_b = np.polyfit(bot_pts[:, 0], bot_pts[:, 1], deg=2)

# Card 2 visualization (Red boundary curves on mask)
vis_2 = vis_1.copy()
cv2.polylines(vis_2, [top_pts.astype(np.int32)], False, (0, 0, 255), 3, cv2.LINE_AA)
cv2.polylines(vis_2, [bot_pts.astype(np.int32)], False, (0, 0, 255), 3, cv2.LINE_AA)

# Card 3: Final bounded solid mask (Zero leaks, Zero holes)
clean_mask = np.zeros_like(mask_crop)
for x_col in range(w):
    col = np.where(mask_filled[:, x_col] > 127)[0]
    if len(col) < 30:
        continue
    yt = int(round(np.polyval(poly_t, x_col)))
    yb = int(round(np.polyval(poly_b, x_col)))
    clean_mask[max(0, yt):min(h-1, yb), x_col] = 255
    
kernel_clean = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel_clean)

vis_3 = np.zeros_like(crop_bgr)
vis_3[clean_mask > 127] = [255, 255, 255]

# Build 3-column comparison
h_target = 550
def scale_im(im):
    w_t = int(round(im.shape[1] * (h_target / float(im.shape[0]))))
    return cv2.resize(im, (w_t, h_target), interpolation=cv2.INTER_LANCZOS4)

def draw_banner(im, text, color):
    b = np.zeros((45, im.shape[1], 3), dtype=np.uint8) + 28
    img_rgb = cv2.cvtColor(b, cv2.COLOR_BGR2RGB)
    pil_im = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_im)
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 15)
    draw.text((10, 12), text, font=font, fill=color)
    res_b = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)
    return np.vstack((res_b, im))

c1 = draw_banner(scale_im(vis_1), "1. Дырки в центре + Проливы", (255, 100, 100))
c2 = draw_banner(scale_im(vis_2), "2. Поиск красных границ T/B", (0, 200, 255))
c3 = draw_banner(scale_im(vis_3), "3. ИТОГ: Дырки залиты, контур четкий", (100, 255, 100))

trio = np.hstack((c1, c2, c3))
hdr = np.zeros((55, trio.shape[1], 3), dtype=np.uint8) + 18
img_rgb = cv2.cvtColor(hdr, cv2.COLOR_BGR2RGB)
pil_hdr = PILImage.fromarray(img_rgb)
draw = ImageDraw.Draw(pil_hdr)
font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 22)
draw.text((20, 14), "Решение: Заливка внутренних дыр и отсечение наружных проливов", font=font, fill=(255, 255, 255))
final_card = np.vstack((cv2.cvtColor(np.array(pil_hdr), cv2.COLOR_RGB2BGR), trio))

out_path = os.path.join(artifacts_dir, "hole_filling_and_leak_prevention_result.png")
cv2.imwrite(out_path, final_card)
print(f"Comparison card saved: {out_path}")
