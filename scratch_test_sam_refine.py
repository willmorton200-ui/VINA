import cv2
import numpy as np
import time
import os
import torch
from pipeline.sam_refiner import SAMRefiner
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

print(f"CUDA Available: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0)}")

# Load SAM ViT-H
t0 = time.perf_counter()
sam = SAMRefiner(model_type="vit_h")
print(f"SAM loaded in {time.perf_counter() - t0:.2f}s. Is ready: {sam.is_ready()}")

stage1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()

for fname in ["monastyrskaya_izba.jpg", "castillo_liria_pair.jpg", "photo_2026-08-11_21-10-14.jpg"]:
    fpath = f"d:/VINA/test_dataset/butilki/{fname}"
    img_bgr = cv2.imread(fpath)
    h, w = img_bgr.shape[:2]
    
    # 1. YOLO detection
    yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.25)
    boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
    confs = yolo_res[0].boxes.conf.cpu().numpy()
    classes = yolo_res[0].boxes.cls.cpu().numpy()
    
    # Pick candidate with penalty scoring
    scored = []
    masks_data = yolo_res[0].masks.data.cpu().numpy() if yolo_res[0].masks is not None else None
    for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs)):
        bx1, by1, bx2, by2 = [int(v) for v in box]
        bw, bh = bx2 - bx1, by2 - by1
        ar = bw / float(bh)
        if 0.35 <= ar <= 1.50 and bw <= 0.65 * w and bh <= 0.75 * h:
            # Check edge contact
            pad_edge = 4
            is_edge = bx1 < pad_edge or by1 < pad_edge or bx2 > w - pad_edge or by2 > h - pad_edge
            area = bw * bh
            score = area - (500000.0 if is_edge else 0.0)
            scored.append((score, box, idx, conf))
            
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_box, best_idx, best_conf = scored[0]
    
    # 2. SAM ViT-H Refinement!
    t_sam = time.perf_counter()
    sam_mask, score_sam = sam.refine_mask(img_bgr, best_box)
    sam_time_ms = (time.perf_counter() - t_sam) * 1000.0
    
    # 3. Tight crop (10px margin)
    coords = cv2.findNonZero(sam_mask)
    x_min = int(np.min(coords[:, 0, 0]))
    x_max = int(np.max(coords[:, 0, 0]))
    y_min = int(np.min(coords[:, 0, 1]))
    y_max = int(np.max(coords[:, 0, 1]))
    pad = 10
    x1 = max(0, x_min - pad)
    y1 = max(0, y_min - pad)
    x2 = min(w, x_max + pad + 1)
    y2 = min(h, y_max + pad + 1)
    
    crop_bgr = img_bgr[y1:y2, x1:x2].copy()
    crop_mask = sam_mask[y1:y2, x1:x2].copy()
    
    # 4. Vectorize
    vec = vectorizer.vectorize(crop_mask)
    vis = crop_bgr.copy()
    cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
    for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 2, cv2.LINE_AA)
        
    os.makedirs("scratch_debug/sam_test", exist_ok=True)
    cv2.imwrite(f"scratch_debug/sam_test/{fname}_sam_mask.png", crop_mask)
    cv2.imwrite(f"scratch_debug/sam_test/{fname}_sam_features.png", vis)
    print(f"[{fname}] SAM ViT-H inference: {sam_time_ms:.1f}ms, Score: {score_sam:.3f}, Crop: {crop_bgr.shape[1]}x{crop_bgr.shape[0]}")

