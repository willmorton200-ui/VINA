import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/castillo_liria_pair.jpg"
img_bgr = cv2.imread(img_path)
h_orig, w_orig = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()

# 1. Segment using YOLOv8x-seg
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.20)
masks_data = yolo_res[0].masks.data.cpu().numpy()
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()

# Find the dominant label mask near center
img_cx = w_orig / 2.0
best_mask = None
best_area = -1
for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs)):
    cls_int = int(cls_id)
    cls_name = stage1.yolo_model.names.get(cls_int, f"class_{cls_int}").lower()
    if cls_int == 0 or "label" in cls_name:
        bx1, by1, bx2, by2 = [int(v) for v in box]
        bw, bh = bx2 - bx1, by2 - by1
        area = bw * bh
        bcx = (bx1 + bx2) / 2.0
        if area > best_area and area >= 0.02 * (w_orig * h_orig):
            best_area = area
            m_raw = masks_data[idx]
            best_mask = (cv2.resize(m_raw, (w_orig, h_orig)) > 0.5).astype(np.uint8) * 255

# Apply photometric paper gate on full image (or bounding box)
coords = cv2.findNonZero(best_mask)
x_min, y_min, w_box, h_box = cv2.boundingRect(coords)
x_max, y_max = x_min + w_box, y_min + h_box

# 2. EXACT TIGHT CROP WITH 5-10 PIXEL MARGIN (PAD = 8 PX)
pad = 8
x1 = max(0, x_min - pad)
y1 = max(0, y_min - pad)
x2 = min(w_orig, x_max + pad)
y2 = min(h_orig, y_max + pad)

tight_crop_bgr = img_bgr[y1:y2, x1:x2].copy()
tight_mask = best_mask[y1:y2, x1:x2].copy()
tight_mask = stage1._apply_photometric_paper_gate(tight_crop_bgr, tight_mask)
tight_mask = stage1._keep_largest_component(tight_mask)

# Re-crop if paper gate trimmed any outer noise
coords_clean = cv2.findNonZero(tight_mask)
if coords_clean is not None:
    cx_min = int(np.min(coords_clean[:, 0, 0]))
    cx_max = int(np.max(coords_clean[:, 0, 0]))
    cy_min = int(np.min(coords_clean[:, 0, 1]))
    cy_max = int(np.max(coords_clean[:, 0, 1]))
    
    # Second tight trim with exact 8px pad
    tx1 = max(0, cx_min - pad)
    ty1 = max(0, cy_min - pad)
    tx2 = min(tight_crop_bgr.shape[1], cx_max + pad)
    ty2 = min(tight_crop_bgr.shape[0], cy_max + pad)
    
    tight_crop_bgr = tight_crop_bgr[ty1:ty2, tx1:tx2].copy()
    tight_mask = tight_mask[ty1:ty2, tx1:tx2].copy()

print(f"Tight crop shape: {tight_crop_bgr.shape[1]}x{tight_crop_bgr.shape[0]}")
c_final = cv2.findNonZero(tight_mask)
fx_min = int(np.min(c_final[:, 0, 0]))
fx_max = int(np.max(c_final[:, 0, 0]))
fy_min = int(np.min(c_final[:, 0, 1]))
fy_max = int(np.max(c_final[:, 0, 1]))
print(f"Mask margins relative to crop: left={fx_min}px, right={tight_crop_bgr.shape[1]-fx_max}px, top={fy_min}px, bottom={tight_crop_bgr.shape[0]-fy_max}px")

# Vectorize
vec = vectorizer.vectorize(tight_mask)
print(f"Corners: P_TL={vec.P_TL}, P_TR={vec.P_TR}, P_BL={vec.P_BL}, P_BR={vec.P_BR}")

# Draw feature overlay
vis = tight_crop_bgr.copy()
cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 2, cv2.LINE_AA)

os.makedirs("scratch_debug", exist_ok=True)
cv2.imwrite("scratch_debug/castillo_tight_crop.png", tight_crop_bgr)
cv2.imwrite("scratch_debug/castillo_tight_mask.png", tight_mask)
cv2.imwrite("scratch_debug/castillo_tight_features.png", vis)
print("Saved scratch_debug/castillo_tight_features.png!")
