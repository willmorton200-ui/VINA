import cv2
import numpy as np
import os
import torch

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)
h_img, w_img = img_bgr.shape[:2]

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()

# The target bottle from user's screenshot is the central/right bottle: [479, 263, 960, 840]
target_box = [479, 263, 960, 840]
bx1, by1, bx2, by2 = target_box
bw, bh = bx2 - bx1, by2 - by1

# ========================================================================
# 1. OLD SAM (Single Box Prompt without Negative Prompts)
# ========================================================================
pad_x = int(bw * 0.04)
pad_y = int(bh * 0.04)
old_prompt_box = [max(0, bx1 - pad_x), max(0, by1 - pad_y), min(w_img, bx2 + pad_x), min(h_img, by2 + pad_y)]
mask_old_full, _ = p1.sam_refiner.refine_mask(img_bgr, old_prompt_box)

# ========================================================================
# 2. TUNED SAM (Prompt Engineering + Negative Glass Points + Multimask + Paper Gate)
# ========================================================================
# ROI
roi_pad_x = int(bw * 0.15)
roi_pad_y = int(bh * 0.15)
rx1, ry1 = max(0, bx1 - roi_pad_x), max(0, by1 - roi_pad_y)
rx2, ry2 = min(w_img, bx2 + roi_pad_x), min(h_img, by2 + roi_pad_y)

roi_bgr = img_bgr[ry1:ry2, rx1:rx2]
roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)

local_box = np.array([bx1 - rx1, by1 - ry1, bx2 - rx1, by2 - ry1], dtype=np.float32).reshape(1, 4)

# Positive points strictly inside label paper (foreground = 1)
pts_pos = [
    [bx1 - rx1 + bw * 0.50, by1 - ry1 + bh * 0.40],
    [bx1 - rx1 + bw * 0.50, by1 - ry1 + bh * 0.65],
    [bx1 - rx1 + bw * 0.30, by1 - ry1 + bh * 0.50],
    [bx1 - rx1 + bw * 0.70, by1 - ry1 + bh * 0.50],
]

# Negative points in the dark glass above the top red curve (background = 0)
pts_neg = [
    [bx1 - rx1 + bw * 0.50, max(0, by1 - ry1 - 10)], # top center glass
    [bx1 - rx1 + bw * 0.20, max(0, by1 - ry1 - 10)], # top left glass
    [bx1 - rx1 + bw * 0.80, max(0, by1 - ry1 - 10)], # top right glass
    [bx1 - rx1 + bw * 0.95, max(0, by1 - ry1 - 10)], # top far-right glass
    [bx1 - rx1 + bw * 0.50, min(ry2 - ry1 - 1, by2 - ry1 + 25)], # bottom shelf
]

all_pts = np.array(pts_pos + pts_neg, dtype=np.float32)
all_labels = np.array([1]*len(pts_pos) + [0]*len(pts_neg), dtype=np.int32)

predictor = p1.sam_refiner.predictor
with torch.no_grad():
    with torch.amp.autocast('cuda', enabled=True, dtype=torch.float16):
        predictor.set_image(roi_rgb)
        
        t_box = predictor.transform.apply_boxes_torch(
            torch.tensor(local_box, device=p1.device),
            roi_rgb.shape[:2]
        )
        t_pts = predictor.transform.apply_coords_torch(
            torch.tensor(all_pts, device=p1.device).unsqueeze(0),
            roi_rgb.shape[:2]
        )
        t_labels = torch.tensor(all_labels, device=p1.device).unsqueeze(0)
        
        # Multimask output: returns 3 hierarchy levels (Whole Object, Subpart, Detail)
        masks, scores, _ = predictor.predict_torch(
            point_coords=t_pts,
            point_labels=t_labels,
            boxes=t_box,
            multimask_output=True
        )

masks_np = masks[0].cpu().numpy().astype(np.uint8) * 255
scores_np = scores[0].cpu().numpy()

# Hierarchy selection: mask with highest stability inside the label
best_idx = int(np.argmax(scores_np))
raw_sam_mask = masks_np[best_idx]

# Photometric Paper Gate (Фильтрация темного стекла L < 80)
lab_roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2LAB)
l_channel = lab_roi[:, :, 0]

masked_l = l_channel[raw_sam_mask > 127]
otsu_thresh, _ = cv2.threshold(masked_l, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
glass_cutoff = max(int(otsu_thresh * 0.65), 75)

clean_mask_roi = raw_sam_mask.copy()
# Glass cutoff only applied in upper 30% where glass leakage happens
top_region = np.zeros_like(clean_mask_roi, dtype=bool)
top_region[:int(by1 - ry1 + bh * 0.30), :] = True
clean_mask_roi[top_region & (l_channel < glass_cutoff)] = 0

# Keep largest component
num_l, labs, stats, _ = cv2.connectedComponentsWithStats(clean_mask_roi, connectivity=8)
if num_l > 1:
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask_roi = np.uint8(labs == largest) * 255

# Morphological close to seal text holes
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
clean_mask_roi = cv2.morphologyEx(clean_mask_roi, cv2.MORPH_CLOSE, kernel)

cnts, _ = cv2.findContours(clean_mask_roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if cnts:
    cv2.drawContours(clean_mask_roi, [max(cnts, key=cv2.contourArea)], -1, 255, -1)

# Full mask
mask_new_full = np.zeros((h_img, w_img), dtype=np.uint8)
mask_new_full[ry1:ry2, rx1:rx2] = clean_mask_roi

# ========================================================================
# CROPPED COMPARISON
# ========================================================================
crop_orig = img_bgr[by1:by2, bx1:bx2]
m_old = mask_old_full[by1:by2, bx1:bx2]
m_new = mask_new_full[by1:by2, bx1:bx2]

# Overlay 1: Old SAM (с захватом темного стекла сверху)
over_old = crop_orig.copy()
over_old[m_old > 127] = cv2.addWeighted(crop_orig[m_old > 127], 0.5, np.full_like(crop_orig[m_old > 127], (0, 0, 255)), 0.5, 0)

# Overlay 2: Tuned SAM (строго по кромке белой бумаги!)
over_new = crop_orig.copy()
over_new[m_new > 127] = cv2.addWeighted(crop_orig[m_new > 127], 0.5, np.full_like(crop_orig[m_new > 127], (0, 255, 0)), 0.5, 0)

# Binary masks side-by-side
m_old_bgr = cv2.cvtColor(m_old, cv2.COLOR_GRAY2BGR)
m_new_bgr = cv2.cvtColor(m_new, cv2.COLOR_GRAY2BGR)

# Header banner
h_c, w_c = crop_orig.shape[:2]
header = np.zeros((45, w_c * 2 + 10, 3), dtype=np.uint8) + 30
cv2.putText(header, "1. До: утечка SAM на темное стекло", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 100, 255), 2, cv2.LINE_AA)
cv2.putText(header, "2. После: настроенный SAM (только наклейка)", (w_c + 20, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 100), 2, cv2.LINE_AA)

divider = np.zeros((h_c, 10, 3), dtype=np.uint8) + 80
montage_over = np.hstack((over_old, divider, over_new))
montage_mask = np.hstack((m_old_bgr, divider, m_new_bgr))

final_montage = np.vstack((header, montage_over, montage_mask))

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "sam_tuned_castillo_medium_sweet.png"), final_montage)
cv2.imwrite(os.path.join(artifacts_dir, "sam_tuned_mask_binary.png"), m_new_bgr)
cv2.imwrite(os.path.join(artifacts_dir, "sam_tuned_overlay_green.png"), over_new)

print("\nSaved sam_tuned_castillo_medium_sweet.png successfully!")
