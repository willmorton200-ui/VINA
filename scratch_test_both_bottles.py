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

# Run YOLO
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.20)
masks_data = yolo_res[0].masks.data.cpu().numpy()
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()

def process_tight_label(idx, box, m_raw, name):
    bx1, by1, bx2, by2 = [int(v) for v in box]
    m_full = (cv2.resize(m_raw, (w_orig, h_orig)) > 0.5).astype(np.uint8) * 255
    
    # Zero out anything outside the specific label bounding box (+10px margin) to prevent bleed from neighboring bottle!
    label_isolated = np.zeros_like(m_full)
    box_pad = 10
    by1_p, by2_p = max(0, by1 - box_pad), min(h_orig, by2 + box_pad)
    bx1_p, bx2_p = max(0, bx1 - box_pad), min(w_orig, bx2 + box_pad)
    label_isolated[by1_p:by2_p, bx1_p:bx2_p] = m_full[by1_p:by2_p, bx1_p:bx2_p]
    
    # Keep only largest connected component inside this isolated box
    clean_mask = stage1._keep_largest_component(label_isolated)
    
    # Find exact non-zero coordinates
    coords = cv2.findNonZero(clean_mask)
    if coords is None:
        return
        
    x_min = int(np.min(coords[:, 0, 0]))
    x_max = int(np.max(coords[:, 0, 0]))
    y_min = int(np.min(coords[:, 0, 1]))
    y_max = int(np.max(coords[:, 0, 1]))
    
    # EXACT TIGHT CROP WITH 5-10 PIXEL MARGIN (PAD = 8 PX)
    pad = 8
    x1 = max(0, x_min - pad)
    y1 = max(0, y_min - pad)
    x2 = min(w_orig, x_max + pad + 1)
    y2 = min(h_orig, y_max + pad + 1)
    
    tight_img = img_bgr[y1:y2, x1:x2].copy()
    tight_mask = clean_mask[y1:y2, x1:x2].copy()
    
    # Photometric gate
    tight_mask = stage1._apply_photometric_paper_gate(tight_img, tight_mask)
    tight_mask = stage1._keep_largest_component(tight_mask)
    
    # Re-verify tight bounds after paper gate
    c_final = cv2.findNonZero(tight_mask)
    fx_min = int(np.min(c_final[:, 0, 0]))
    fx_max = int(np.max(c_final[:, 0, 0]))
    fy_min = int(np.min(c_final[:, 0, 1]))
    fy_max = int(np.max(c_final[:, 0, 1]))
    
    tx1 = max(0, fx_min - pad)
    ty1 = max(0, fy_min - pad)
    tx2 = min(tight_img.shape[1], fx_max + pad + 1)
    ty2 = min(tight_img.shape[0], fy_max + pad + 1)
    
    tight_img = tight_img[ty1:ty2, tx1:tx2].copy()
    tight_mask = tight_mask[ty1:ty2, tx1:tx2].copy()
    
    # Vectorize
    vec = vectorizer.vectorize(tight_mask)
    
    vis = tight_img.copy()
    cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 2, cv2.LINE_AA)
        
    cv2.imwrite(f"scratch_debug/{name}_tight_features.png", vis)
    print(f"[{name}] Dimensions: {tight_img.shape[1]}x{tight_img.shape[0]}, Margins: left={fx_min-tx1}px, right={tx2-fx_max-1}px, top={fy_min-ty1}px, bottom={ty2-fy_max-1}px")

# Process Left Red bottle (Det 0)
process_tight_label(0, boxes[0], masks_data[0], "castillo_red")

# Process Right White bottle (Det 4)
process_tight_label(4, boxes[4], masks_data[4], "castillo_white")
