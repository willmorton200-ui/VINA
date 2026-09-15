import cv2
import numpy as np
import os
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

sam = SAMRefiner(model_type="vit_h")
box0 = [191, 700, 903, 2197]
bx1, by1, bx2, by2 = box0
bw, bh = bx2 - bx1, by2 - by1

# Test Method A: SAM with Box + 4 Corner Inward Prompts
# 4 points placed 5% inside each corner of the bounding box
margin_x = int(bw * 0.06)
margin_y = int(bh * 0.06)
pts_prompt = np.array([
    [bx1 + margin_x, by1 + margin_y], # Top-Left
    [bx2 - margin_x, by1 + margin_y], # Top-Right
    [bx1 + margin_x, by2 - margin_y], # Bottom-Left
    [bx2 - margin_x, by2 - margin_y], # Bottom-Right
    [(bx1 + bx2) // 2, (by1 + by2) // 2] # Center
], dtype=np.float32)
labels_prompt = np.array([1, 1, 1, 1, 1], dtype=np.int32)

# ROI prediction
pad_x = int(bw * 0.15)
pad_y = int(bh * 0.15)
rx1, ry1 = max(0, bx1 - pad_x), max(0, by1 - pad_y)
rx2, ry2 = min(w, bx2 + pad_x), min(h, by2 + pad_y)

roi_bgr = img_bgr[ry1:ry2, rx1:rx2].copy()
roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
sam.predictor.set_image(roi_rgb)

roi_box = np.array([bx1 - rx1, by1 - ry1, bx2 - rx1, by2 - ry1], dtype=np.float32)
roi_pts = pts_prompt - np.array([rx1, ry1], dtype=np.float32)

masks, scores, _ = sam.predictor.predict(
    point_coords=roi_pts,
    point_labels=labels_prompt,
    box=roi_box[None, :],
    multimask_output=True
)

best_idx = np.argmax(scores)
mask_guided = masks[best_idx].astype(np.uint8) * 255

full_mask_A = np.zeros((h, w), dtype=np.uint8)
full_mask_A[ry1:ry2, rx1:rx2] = mask_guided

# Tight crop with 10px margin
coords = cv2.findNonZero(full_mask_A)
cx1 = max(0, int(np.min(coords[:, 0, 0])) - 10)
cy1 = max(0, int(np.min(coords[:, 0, 1])) - 10)
cx2 = min(w, int(np.max(coords[:, 0, 0])) + 11)
cy2 = min(h, int(np.max(coords[:, 0, 1])) + 11)

crop_A_bgr = img_bgr[cy1:cy2, cx1:cx2].copy()
crop_A_mask = full_mask_A[cy1:cy2, cx1:cx2].copy()

# Vectorize
vectorizer = MaskVectorizer()
vec_A = vectorizer.vectorize(crop_A_mask)

vis_A = crop_A_bgr.copy()
cv2.polylines(vis_A, [vec_A.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_A, [vec_A.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_A, [vec_A.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_A, [vec_A.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec_A.P_TL, vec_A.P_TR, vec_A.P_BL, vec_A.P_BR]:
    cv2.circle(vis_A, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_A, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)

os.makedirs("scratch_debug/alma_guided", exist_ok=True)
cv2.imwrite("scratch_debug/alma_guided/crop_mask_A.png", crop_A_mask)
cv2.imwrite("scratch_debug/alma_guided/features_A.png", vis_A)

print("Saved scratch_debug/alma_guided/features_A.png!")
print(f"P_TL: {vec_A.P_TL}, P_TR: {vec_A.P_TR}, P_BL: {vec_A.P_BL}, P_BR: {vec_A.P_BR}")
