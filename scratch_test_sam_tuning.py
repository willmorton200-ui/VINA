import cv2
import numpy as np
import os
import torch

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)
h_img, w_img = img_bgr.shape[:2]

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()

# 1. Run YOLO to get label bounding box
results = p1.yolo_model.predict(img_bgr, verbose=False, device=p1.device, conf=0.25)
target_box = None
for r in results:
    if r.boxes is not None and len(r.boxes) > 0:
        boxes = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy()
        # Find best label box
        for box, conf, cls_id in zip(boxes, confs, classes):
            cls_name = p1.yolo_model.names.get(int(cls_id), "")
            if int(cls_id) == 0 or "label" in cls_name.lower():
                target_box = [int(v) for v in box]
                break

if target_box is None:
    target_box = [int(w_img*0.1), int(h_img*0.1), int(w_img*0.9), int(h_img*0.9)]

print(f"Target Label Bounding Box: {target_box}")

# ------------------------------------------------------------------
# Test 1: Current SAM behavior (Single box prompt)
# ------------------------------------------------------------------
mask_v1, score_v1 = p1.sam_refiner.refine_mask(img_bgr, target_box)

# ------------------------------------------------------------------
# Test 2: SAM with Point Prompts (Positive center points + Negative glass points)
# ------------------------------------------------------------------
x1, y1, x2, y2 = target_box
bw, bh = x2 - x1, y2 - y1

# Positive points inside label
pts_pos = [
    [x1 + bw * 0.50, y1 + bh * 0.35],
    [x1 + bw * 0.50, y1 + bh * 0.50],
    [x1 + bw * 0.50, y1 + bh * 0.65],
    [x1 + bw * 0.25, y1 + bh * 0.50],
    [x1 + bw * 0.75, y1 + bh * 0.50],
]
# Negative points in the glass above the label (where SAM was leaking)
pts_neg = [
    [x1 + bw * 0.50, max(0, y1 - 20)],
    [x1 + bw * 0.25, max(0, y1 - 20)],
    [x1 + bw * 0.75, max(0, y1 - 20)],
]

all_pts = np.array(pts_pos + pts_neg, dtype=np.float32)
all_labels = np.array([1]*len(pts_pos) + [0]*len(pts_neg), dtype=np.int32)

# Run SAM with point prompts + multimask selection
roi_pad_x = int(bw * 0.20)
roi_pad_y = int(bh * 0.20)
rx1, ry1 = max(0, x1 - roi_pad_x), max(0, y1 - roi_pad_y)
rx2, ry2 = min(w_img, x2 + roi_pad_x), min(h_img, y2 + roi_pad_y)

roi_bgr = img_bgr[ry1:ry2, rx1:rx2]
roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)

predictor = p1.sam_refiner.predictor
with torch.no_grad():
    with torch.amp.autocast('cuda', enabled=True, dtype=torch.float16):
        predictor.set_image(roi_rgb)
        
        local_box = np.array([x1 - rx1, y1 - ry1, x2 - rx1, y2 - ry1], dtype=np.float32).reshape(1, 4)
        local_pts = all_pts.copy()
        local_pts[:, 0] -= rx1
        local_pts[:, 1] -= ry1
        
        t_box = predictor.transform.apply_boxes_torch(torch.tensor(local_box, device=p1.device), roi_rgb.shape[:2])
        t_pts = predictor.transform.apply_coords_torch(torch.tensor(local_pts, device=p1.device).unsqueeze(0), roi_rgb.shape[:2])
        t_labels = torch.tensor(all_labels, device=p1.device).unsqueeze(0)
        
        masks, scores, _ = predictor.predict_torch(
            point_coords=t_pts,
            point_labels=t_labels,
            boxes=t_box,
            multimask_output=True # evaluate 3 hierarchy levels
        )

masks_np = masks[0].cpu().numpy().astype(np.uint8) * 255
scores_np = scores[0].cpu().numpy()

print(f"SAM Multimask scores: {scores_np}")

# ------------------------------------------------------------------
# Test 3: Photometric Paper Boundary Post-Filtering (Color & Gradient Gate)
# ------------------------------------------------------------------
# The bottle glass has dark luminance (L < 90) or high color contrast against white paper
lab_roi = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2LAB)
l_channel = lab_roi[:, :, 0]

# Pick mask 0, 1, 2
best_mask_idx = np.argmax(scores_np)
sam_candidate = masks_np[best_mask_idx]

# Gate: paper label has high luminance compared to dark glass
# Compute Otsu threshold on the masked region
masked_pixels = l_channel[sam_candidate > 127]
if len(masked_pixels) > 100:
    l_thresh, _ = cv2.threshold(masked_pixels, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # Glass cutoff: remove dark glass pixels at the top border of the mask
    glass_mask = (l_channel < max(l_thresh * 0.70, 70)) & (sam_candidate > 127)
    
    clean_sam_roi = sam_candidate.copy()
    clean_sam_roi[glass_mask] = 0
    
    # Keep largest connected component (the clean paper label)
    num_l, labs, stats, _ = cv2.connectedComponentsWithStats(clean_sam_roi, connectivity=8)
    if num_l > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        clean_sam_roi = np.uint8(labs == largest) * 255
else:
    clean_sam_roi = sam_candidate

# Morphological close to seal internal text
clean_sam_roi = cv2.morphologyEx(clean_sam_roi, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))

# Paste back to full image
mask_v2 = np.zeros((h_img, w_img), dtype=np.uint8)
mask_v2[ry1:ry2, rx1:rx2] = clean_sam_roi

# Crop regions for visualization
crop_orig = img_bgr[target_box[1]:target_box[3], target_box[0]:target_box[2]]
crop_m1 = mask_v1[target_box[1]:target_box[3], target_box[0]:target_box[2]]
crop_m2 = mask_v2[target_box[1]:target_box[3], target_box[0]:target_box[2]]

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"

cv2.imwrite(os.path.join(artifacts_dir, "sam_comparison_v1_old.png"), crop_m1)
cv2.imwrite(os.path.join(artifacts_dir, "sam_comparison_v2_clean.png"), crop_m2)

# Overlay on crop
over_v1 = crop_orig.copy()
over_v1[crop_m1 > 127] = cv2.addWeighted(crop_orig[crop_m1 > 127], 0.5, np.full_like(crop_orig[crop_m1 > 127], (0, 0, 255)), 0.5, 0)

over_v2 = crop_orig.copy()
over_v2[crop_m2 > 127] = cv2.addWeighted(crop_orig[crop_m2 > 127], 0.5, np.full_like(crop_orig[crop_m2 > 127], (0, 255, 0)), 0.5, 0)

comparison_panel = np.hstack((over_v1, np.full((crop_orig.shape[0], 10, 3), 80, dtype=np.uint8), over_v2))
cv2.imwrite(os.path.join(artifacts_dir, "sam_tuning_comparison.png"), comparison_panel)

print("Saved sam_tuning_comparison.png successfully!")
