import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

p1 = Stage1Preprocessor()

# Process with Stage 1
crop_bgr, raw_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_bgr.shape[:2]

# Apply Photometric Paper Gate (Решение 3)
lab = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB)
l_channel = lab[:, :, 0]

masked_pixels = l_channel[raw_mask > 127]
otsu_thresh, _ = cv2.threshold(masked_pixels, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
glass_cutoff = max(int(otsu_thresh * 0.65), 75)

y_indices, _ = np.where(raw_mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
H_mask = y_max - y_min

clean_mask = raw_mask.copy()
top_glass_zone = np.zeros((h, w), dtype=bool)
top_glass_zone[:int(y_min + H_mask * 0.35), :] = True
clean_mask[top_glass_zone & (l_channel < glass_cutoff)] = 0

# Keep largest component
clean_mask = p1._keep_largest_component(clean_mask)

# Morph close & fill holes
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel)
cnts, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if cnts:
    cv2.drawContours(clean_mask, [max(cnts, key=cv2.contourArea)], -1, 255, -1)

# Visualization
vis_raw = crop_bgr.copy()
vis_raw[raw_mask > 127] = cv2.addWeighted(crop_bgr[raw_mask > 127], 0.5, np.full_like(crop_bgr[raw_mask > 127], (0, 0, 255)), 0.5, 0)

vis_clean = crop_bgr.copy()
vis_clean[clean_mask > 127] = cv2.addWeighted(crop_bgr[clean_mask > 127], 0.5, np.full_like(crop_bgr[clean_mask > 127], (0, 255, 0)), 0.5, 0)

raw_mask_bgr = cv2.cvtColor(raw_mask, cv2.COLOR_GRAY2BGR)
clean_mask_bgr = cv2.cvtColor(clean_mask, cv2.COLOR_GRAY2BGR)

header = np.zeros((45, w * 2 + 10, 3), dtype=np.uint8) + 30
cv2.putText(header, "1. До: Сырая маска SAM (захват темного стекла)", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 100, 255), 2, cv2.LINE_AA)
cv2.putText(header, "2. После: Решение 3 (Цветовой шлюз - только бумага)", (w + 20, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 100), 2, cv2.LINE_AA)

divider = np.zeros((h, 10, 3), dtype=np.uint8) + 80
montage_over = np.hstack((vis_raw, divider, vis_clean))
montage_mask = np.hstack((raw_mask_bgr, divider, clean_mask_bgr))
final_montage = np.vstack((header, montage_over, montage_mask))

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "castillo_solution_3_paper_gate_test.png"), final_montage)
print("Saved castillo_solution_3_paper_gate_test.png successfully!")
