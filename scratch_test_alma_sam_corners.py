import cv2
import numpy as np
import os
from pipeline.sam_refiner import SAMRefiner

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

sam = SAMRefiner(model_type="vit_h")

# Test 1: SAM on Box 0: [191, 700, 903, 2197]
box0 = [191, 700, 903, 2197]
mask0, score0 = sam.refine_mask(img_bgr, box0)

# Test 2: SAM on Box 0 with 4 corner point prompts to force rectangular paper corners!
# Points inside the 4 corners of the label
pts = np.array([
    [230, 750],  # Top-Left corner of black paper
    [870, 750],  # Top-Right corner of black paper
    [230, 2150], # Bottom-Left corner of black paper
    [870, 2150], # Bottom-Right corner of black paper
    [550, 1450]  # Center of label
], dtype=np.float32)
labels = np.array([1, 1, 1, 1, 1], dtype=np.int32)

# Run SAM with point prompts if supported
predictor = sam.predictor
bx1, by1, bx2, by2 = box0
# pad
pad_x = int((bx2 - bx1) * 0.15)
pad_y = int((by2 - by1) * 0.15)
rx1, ry1 = max(0, bx1 - pad_x), max(0, by1 - pad_y)
rx2, ry2 = min(w, bx2 + pad_x), min(h, by2 + pad_y)

roi_bgr = img_bgr[ry1:ry2, rx1:rx2].copy()
roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
predictor.set_image(roi_rgb)

roi_box = np.array([bx1 - rx1, by1 - ry1, bx2 - rx1, by2 - ry1], dtype=np.float32)
roi_pts = pts - np.array([rx1, ry1], dtype=np.float32)

masks, scores, logits = predictor.predict(
    point_coords=roi_pts,
    point_labels=labels,
    box=roi_box[None, :],
    multimask_output=True
)

best_idx = np.argmax(scores)
mask_roi = masks[best_idx].astype(np.uint8) * 255

full_mask_guided = np.zeros((h, w), dtype=np.uint8)
full_mask_guided[ry1:ry2, rx1:rx2] = mask_roi

os.makedirs("scratch_debug/alma_reserve", exist_ok=True)
cv2.imwrite("scratch_debug/alma_reserve/mask_box0.png", mask0)
cv2.imwrite("scratch_debug/alma_reserve/mask_guided.png", full_mask_guided)

# Crop with 10px margin
coords = cv2.findNonZero(mask_roi)
cx1 = max(0, int(np.min(coords[:, 0, 0])) - 10)
cy1 = max(0, int(np.min(coords[:, 0, 1])) - 10)
cx2 = min(roi_bgr.shape[1], int(np.max(coords[:, 0, 0])) + 11)
cy2 = min(roi_bgr.shape[0], int(np.max(coords[:, 0, 1])) + 11)

crop_g_bgr = roi_bgr[cy1:cy2, cx1:cx2]
crop_g_mask = mask_roi[cy1:cy2, cx1:cx2]

cv2.imwrite("scratch_debug/alma_reserve/crop_guided_bgr.png", crop_g_bgr)
cv2.imwrite("scratch_debug/alma_reserve/crop_guided_mask.png", crop_g_mask)
print(f"Mask Box0 NonZero: {np.sum(mask0 > 0)}, Mask Guided NonZero: {np.sum(full_mask_guided > 0)}")
