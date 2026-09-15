import cv2
import numpy as np
import os
import time

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]
print(f"Loaded {img_path}: {w}x{h}")

stage1 = Stage1Preprocessor(use_gpu=True)
sam = SAMRefiner(model_type="vit_h")
vectorizer = MaskVectorizer()

# 1. Inspect YOLO predictions
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.15)
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
masks_data = yolo_res[0].masks.data.cpu().numpy() if yolo_res[0].masks is not None else None

print(f"Detected {len(boxes)} boxes:")
for idx, (b, c, cls_id) in enumerate(zip(boxes, confs, classes)):
    bx1, by1, bx2, by2 = [int(v) for v in b]
    print(f"  Box {idx}: [{bx1}, {by1}, {bx2}, {by2}] (w={bx2-bx1}, h={by2-by1}, conf={c:.2f}, cls={cls_id})")

# Let's inspect SAM mask on the main box
# Find dominant label box
winner_box = None
max_area = 0
for b, c in zip(boxes, confs):
    bx1, by1, bx2, by2 = [int(v) for v in b]
    area = (bx2 - bx1) * (by2 - by1)
    if area > max_area:
        max_area = area
        winner_box = [bx1, by1, bx2, by2]

print(f"\nDominant YOLO Box: {winner_box}")

# Generate SAM ViT-H mask with box prompt
sam_mask, score = sam.refine_mask(img_bgr, winner_box)
print(f"SAM ViT-H score: {score:.3f}")

# Also let's check what stage1.segment_bottle_and_label does!
crop_bgr, crop_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)
print(f"Stage 1 crop_bgr shape: {crop_bgr.shape}, crop_mask shape: {crop_mask.shape}")

# Save debug images
os.makedirs("scratch_debug/alma_reserve", exist_ok=True)
cv2.imwrite("scratch_debug/alma_reserve/sam_raw_mask.png", sam_mask)
cv2.imwrite("scratch_debug/alma_reserve/crop_bgr.png", crop_bgr)
cv2.imwrite("scratch_debug/alma_reserve/crop_mask.png", crop_mask)

# Check vectorization
vec = vectorizer.vectorize(crop_mask)
vis = crop_bgr.copy()
cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite("scratch_debug/alma_reserve/vector_features.png", vis)
print("Saved debug images in scratch_debug/alma_reserve/")
