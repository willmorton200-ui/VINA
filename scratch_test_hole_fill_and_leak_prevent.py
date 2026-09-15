import cv2
import numpy as np
import os
import matplotlib.pyplot as plt

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

# 1. Get SAM mask for both labels or dominant bottle label
# Dominant bottle label box: [239, 366, 673, 1115]
prompt_box = [235, 360, 675, 1120]
mask_raw, score = p1.sam_refiner.refine_mask(img, prompt_box)

crop_bgr = img[340:1150, 220:700].copy()
mask_crop = mask_raw[340:1150, 220:700].copy()
h, w = crop_bgr.shape[:2]

# --- ALGORITHM: 1. FILL ALL INTERNAL HOLES & GAPS ---
# A: Fill holes by taking the external hull/contour
binary = np.uint8(mask_crop > 127) * 255
# Morphological closing vertically to bridge the thin horizontal gap between labels
kernel_vert = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 21))
mask_bridged = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_vert)

# Fill all enclosed internal holes
cnts, _ = cv2.findContours(mask_bridged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
mask_filled = np.zeros_like(binary)
if cnts:
    largest_cnt = max(cnts, key=cv2.contourArea)
    cv2.drawContours(mask_filled, [largest_cnt], -1, 255, -1)

# --- ALGORITHM: 2. PREVENT OUTER CONTOUR LEAKAGE (TOP & BOTTOM CUTOFF) ---
# Find exact top edge and bottom arc using gradient / color contrast transition
# In Barakiani: Paper is light beige (L > 100, BGR around [160, 190, 200]), Glass is dark (L < 60)
lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
l_channel = lab[:, :, 0]

# Gradient magnitude along Y
sobel_y = cv2.Sobel(l_channel, cv2.CV_64F, 0, 1, ksize=3)

# Extract column-by-column the TRUE top edge and TRUE bottom arc
# Top edge: sharpest positive gradient transition (dark glass -> light paper)
# Bottom edge: sharpest negative gradient transition (light paper -> dark glass)
xs = np.where(mask_filled > 127)[1]
unique_xs = np.unique(xs)

top_edge_pts = []
bot_edge_pts = []

for x_col in range(w):
    col_mask = np.where(mask_filled[:, x_col] > 127)[0]
    if len(col_mask) < 20:
        continue
    y_start, y_end = col_mask[0], col_mask[-1]
    
    # 1. Search for Top Edge near y_start (-15 to +35 px)
    y_top_search_min = max(0, y_start - 15)
    y_top_search_max = min(h - 1, y_start + 40)
    top_grads = sobel_y[y_top_search_min:y_top_search_max, x_col]
    if len(top_grads) > 0:
        best_top_y = y_top_search_min + np.argmax(top_grads)
    else:
        best_top_y = y_start
    top_edge_pts.append((x_col, best_top_y))
    
    # 2. Search for Bottom Edge near y_end (-40 to +20 px)
    y_bot_search_min = max(0, y_end - 50)
    y_bot_search_max = min(h - 1, y_end + 20)
    # Bottom transition is paper -> glass, so sobel_y is negative (minimum)
    bot_grads = sobel_y[y_bot_search_min:y_bot_search_max, x_col]
    if len(bot_grads) > 0:
        best_bot_y = y_bot_search_min + np.argmin(bot_grads)
    else:
        best_bot_y = y_end
    bot_edge_pts.append((x_col, best_bot_y))

top_edge_pts = np.array(top_edge_pts)
bot_edge_pts = np.array(bot_edge_pts)

# Robust smooth fit of top curve (parabola / line) and bottom curve (convex smile parabola)
poly_top = np.polyfit(top_edge_pts[:, 0], top_edge_pts[:, 1], deg=2)
poly_bot = np.polyfit(bot_edge_pts[:, 0], bot_edge_pts[:, 1], deg=2)

# Build strictly bounded mask (No leakage at top, No leakage at bottom)
bounded_mask = np.zeros_like(binary)
for x_col in range(w):
    col_mask = np.where(mask_filled[:, x_col] > 127)[0]
    if len(col_mask) < 20:
        continue
    
    y_t_curve = int(round(np.polyval(poly_top, x_col)))
    y_b_curve = int(round(np.polyval(poly_bot, x_col)))
    
    # Clip strictly between top curve and bottom curve
    y_t_valid = max(0, y_t_curve)
    y_b_valid = min(h - 1, y_b_curve)
    
    if y_b_valid > y_t_valid:
        bounded_mask[y_t_valid:y_b_valid, x_col] = 255

# Fill internal & smooth perimeter
kernel_clean = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
bounded_mask = cv2.morphologyEx(bounded_mask, cv2.MORPH_CLOSE, kernel_clean)

# Visual comparison card
# 1. Raw leaky mask with holes
# 2. Perfect filled & bounded mask
vis_leak = np.zeros_like(crop_bgr)
vis_leak[mask_crop > 127] = [255, 255, 255]

vis_perfect = np.zeros_like(crop_bgr)
vis_perfect[bounded_mask > 127] = [255, 255, 255]

# Overlay red lines on vis_leak to demonstrate what was fixed
cv2.polylines(vis_leak, [top_edge_pts.astype(np.int32)], False, (0, 0, 255), 3, cv2.LINE_AA)
cv2.polylines(vis_leak, [bot_edge_pts.astype(np.int32)], False, (0, 0, 255), 3, cv2.LINE_AA)

cv2.imwrite(f"{artifacts_dir}/barakiani_bounded_mask_fixed.png", bounded_mask)
cv2.imwrite(f"{artifacts_dir}/barakiani_raw_mask_leak_vis.png", vis_leak)

print("Saved bounded mask and leak visualization!")
