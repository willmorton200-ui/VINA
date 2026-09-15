import cv2
import numpy as np
import os
import glob
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer
from pipeline.dewarp_engine import CylindricalDewarpEngine

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-12.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.10)

boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
masks_data = yolo_res[0].masks.data.cpu().numpy() if yolo_res[0].masks is not None else None

scored_candidates = []
for idx, (b, c, cls_id) in enumerate(zip(boxes, confs, classes)):
    bx1, by1, bx2, by2 = [int(v) for v in b]
    bw_box, bh_box = max(1, bx2 - bx1), max(1, by2 - by1)
    ar = bw_box / float(bh_box)
    
    # 1. Reject cut-off boxes touching photo border (10px margin)
    touches_border = (bx1 <= 10 or by1 <= 10 or bx2 >= w - 10 or by2 >= h - 10)
    
    # 2. Aspect ratio & size filter for wine labels
    valid_size = (0.20 <= ar <= 2.20 and bw_box <= 0.85 * w and bh_box <= 0.90 * h)
    
    if masks_data is not None and idx < len(masks_data):
        m_raw = masks_data[idx]
        m_full = (cv2.resize(m_raw, (w, h)) > 0.5).astype(np.uint8) * 255
        m_full = stage1._keep_largest_component(m_full)
        pixel_area = np.count_nonzero(m_full)
        
        # Centrality factor: target bottle is centered in camera frame
        cx_box = (bx1 + bx2) / 2.0
        dist_from_center_ratio = abs(cx_box - w / 2.0) / (w / 2.0)
        centrality_weight = max(0.2, 1.0 - 0.6 * dist_from_center_ratio)
        
        # Heavy penalty if touching frame border
        border_penalty = 5000000.0 if touches_border else 0.0
        score = (pixel_area * centrality_weight) - border_penalty
        
        if valid_size and pixel_area >= 0.015 * (w * h):
            scored_candidates.append({
                "idx": idx,
                "box": [bx1, by1, bx2, by2],
                "area": pixel_area,
                "touches_border": touches_border,
                "centrality_weight": centrality_weight,
                "score": score
            })

scored_candidates.sort(key=lambda item: item["score"], reverse=True)
print("Top candidate winner:")
winner = scored_candidates[0]
print(winner)

# Let's test SAM + Dewarp on this winning Box 0: [239, 817, 938, 1916]
sam = SAMRefiner(model_type="vit_h")
sam_mask, score = sam.refine_mask(img_bgr, winner["box"])

# Crop with 10px margin
coords = cv2.findNonZero(sam_mask)
cx1 = max(0, int(np.min(coords[:, 0, 0])) - 10)
cy1 = max(0, int(np.min(coords[:, 0, 1])) - 10)
cx2 = min(w, int(np.max(coords[:, 0, 0])) + 11)
cy2 = min(h, int(np.max(coords[:, 0, 1])) + 11)

crop_bgr = img_bgr[cy1:cy2, cx1:cx2].copy()
crop_mask = sam_mask[cy1:cy2, cx1:cx2].copy()

vec = MaskVectorizer()
v = vec.vectorize(crop_mask)

vis = crop_bgr.copy()
cv2.polylines(vis, [v.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [v.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [v.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [v.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [v.P_TL, v.P_TR, v.P_BL, v.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)

os.makedirs("scratch_debug/alma_chardonnay_fixed", exist_ok=True)
cv2.imwrite("scratch_debug/alma_chardonnay_fixed/crop_bgr.png", crop_bgr)
cv2.imwrite("scratch_debug/alma_chardonnay_fixed/crop_mask.png", crop_mask)
cv2.imwrite("scratch_debug/alma_chardonnay_fixed/vector_features.png", vis)
print("Saved scratch_debug/alma_chardonnay_fixed/vector_features.png!")
