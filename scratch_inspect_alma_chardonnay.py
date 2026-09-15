import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-12.jpg"
img_bgr = cv2.imread(img_path)
if img_bgr is None:
    print(f"Error loading {img_path}")
    exit(1)
h, w = img_bgr.shape[:2]
print(f"Loaded {img_path}: {w}x{h}")

stage1 = Stage1Preprocessor(use_gpu=True)
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.10)

boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
masks_data = yolo_res[0].masks.data.cpu().numpy() if yolo_res[0].masks is not None else None

print(f"\n--- YOLO Detections ({len(boxes)} boxes) ---")
for idx, (b, c, cls_id) in enumerate(zip(boxes, confs, classes)):
    bx1, by1, bx2, by2 = [int(v) for v in b]
    bw, bh = bx2 - bx1, by2 - by1
    ar = bw / max(1, bh)
    center_x = (bx1 + bx2) / 2
    dist_to_center = abs(center_x - w/2)
    print(f"Box {idx}: [{bx1}, {by1}, {bx2}, {by2}] (w={bw}, h={bh}, ar={ar:.2f}, conf={c:.2f}, dist_center={dist_to_center:.1f})")

# Let's see what stage1.segment_bottle_and_label selects
crop_bgr, crop_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)
print("\n--- Stage 1 Result ---")
print("bbox_info:", {k: v for k, v in bbox_info.items() if k != "vector_mask"})

os.makedirs("scratch_debug/alma_chardonnay", exist_ok=True)
cv2.imwrite("scratch_debug/alma_chardonnay/crop_bgr.png", crop_bgr)
cv2.imwrite("scratch_debug/alma_chardonnay/crop_mask.png", crop_mask)

# Vectorize
vectorizer = MaskVectorizer()
vec = vectorizer.vectorize(crop_mask)
vis = crop_bgr.copy()
cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)
cv2.imwrite("scratch_debug/alma_chardonnay/vector_features.png", vis)
print("Saved debug images in scratch_debug/alma_chardonnay/")
