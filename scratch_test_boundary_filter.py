import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/castillo_liria_pair.jpg"
img_bgr = cv2.imread(img_path)
H, W = img_bgr.shape[:2]
print(f"Loaded image: {W}x{H}")

stage1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()

# Run YOLO
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.20)
masks_data = yolo_res[0].masks.data.cpu().numpy()
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()

print(f"\n--- ANALYZING ALL {len(boxes)} CANDIDATE DETECTIONS ---")
valid_candidates = []

for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs)):
    cls_int = int(cls_id)
    cls_name = stage1.yolo_model.names.get(cls_int, f"class_{cls_int}").lower()
    
    if cls_int == 0 or "label" in cls_name:
        m_raw = masks_data[idx]
        m_full = (cv2.resize(m_raw, (W, H)) > 0.5).astype(np.uint8) * 255
        
        # Keep largest component
        m_full = stage1._keep_largest_component(m_full)
        
        # Count border contact pixels
        top_contact = np.count_nonzero(m_full[0, :])
        bot_contact = np.count_nonzero(m_full[H - 1, :])
        left_contact = np.count_nonzero(m_full[:, 0])
        right_contact = np.count_nonzero(m_full[:, W - 1])
        total_border_contact = top_contact + bot_contact + left_contact + right_contact
        
        # Calculate actual non-zero pixel area
        pixel_area = np.count_nonzero(m_full)
        
        is_truncated = total_border_contact > 10
        print(f"Det {idx}: box={[int(v) for v in box]}, pixel_area={pixel_area}, border_contact={total_border_contact} (top={top_contact}, bot={bot_contact}, left={left_contact}, right={right_contact}) -> Truncated: {is_truncated}")
        
        if not is_truncated and pixel_area >= 0.02 * (W * H):
            valid_candidates.append({
                "idx": idx,
                "box": box,
                "area": pixel_area,
                "mask": m_full,
                "conf": float(conf)
            })

print(f"\nFound {len(valid_candidates)} valid non-truncated candidates.")
if valid_candidates:
    # Sort strictly by largest pixel area
    valid_candidates.sort(key=lambda c: c["area"], reverse=True)
    winner = valid_candidates[0]
    print(f"WINNER: Det {winner['idx']} with area={winner['area']} (box={[int(v) for v in winner['box']]})")
    
    # 2. EXACT CROP WITH 10 PX MARGIN
    coords = cv2.findNonZero(winner["mask"])
    x_min = int(np.min(coords[:, 0, 0]))
    x_max = int(np.max(coords[:, 0, 0]))
    y_min = int(np.min(coords[:, 0, 1]))
    y_max = int(np.max(coords[:, 0, 1]))
    
    pad = 10
    x1 = max(0, x_min - pad)
    y1 = max(0, y_min - pad)
    x2 = min(W, x_max + pad + 1)
    y2 = min(H, y_max + pad + 1)
    
    crop_bgr = img_bgr[y1:y2, x1:x2].copy()
    crop_mask = winner["mask"][y1:y2, x1:x2].copy()
    
    # Apply paper gate
    crop_mask = stage1._apply_photometric_paper_gate(crop_bgr, crop_mask)
    crop_mask = stage1._keep_largest_component(crop_mask)
    
    # Re-crop if paper gate trimmed outer glass
    c_clean = cv2.findNonZero(crop_mask)
    cx_min = int(np.min(c_clean[:, 0, 0]))
    cx_max = int(np.max(c_clean[:, 0, 0]))
    cy_min = int(np.min(c_clean[:, 0, 1]))
    cy_max = int(np.max(c_clean[:, 0, 1]))
    
    tx1 = max(0, cx_min - pad)
    ty1 = max(0, cy_min - pad)
    tx2 = min(crop_bgr.shape[1], cx_max + pad + 1)
    ty2 = min(crop_bgr.shape[0], cy_max + pad + 1)
    
    crop_bgr = crop_bgr[ty1:ty2, tx1:tx2].copy()
    crop_mask = crop_mask[ty1:ty2, tx1:tx2].copy()
    
    print(f"Final Crop Size: {crop_bgr.shape[1]}x{crop_bgr.shape[0]}")
    
    # Vectorize
    vec = vectorizer.vectorize(crop_mask)
    
    vis = crop_bgr.copy()
    cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 2, cv2.LINE_AA)
        
    cv2.imwrite("scratch_debug/winner_castillo_white_mask.png", crop_mask)
    cv2.imwrite("scratch_debug/winner_castillo_white_features.png", vis)
    print("Saved scratch_debug/winner_castillo_white_features.png!")
