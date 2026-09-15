import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/castillo_liria_pair.jpg"
img_bgr = cv2.imread(img_path)
H, W = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()

# Run YOLO
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.25)
masks_data = yolo_res[0].masks.data.cpu().numpy()
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()

scored_candidates = []
for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs)):
    cls_int = int(cls_id)
    cls_name = stage1.yolo_model.names.get(cls_int, f"class_{cls_int}").lower()
    
    if cls_int == 0 or "label" in cls_name:
        bx1, by1, bx2, by2 = [int(v) for v in box]
        bw, bh = bx2 - bx1, by2 - by1
        ar = bw / float(bh)
        
        # Discard tiny shelf price tags or whole-frame boxes
        if 0.35 <= ar <= 1.50 and bw <= 0.65 * W and bh <= 0.75 * H:
            m_raw = masks_data[idx]
            m_full = (cv2.resize(m_raw, (W, H)) > 0.5).astype(np.uint8) * 255
            clean_m = stage1._keep_largest_component(m_full)
            
            top_c = np.count_nonzero(clean_m[:2, :])
            bot_c = np.count_nonzero(clean_m[H-2:, :])
            left_c = np.count_nonzero(clean_m[:, :2])
            right_c = np.count_nonzero(clean_m[:, W-2:])
            border_c = top_c + bot_c + left_c + right_c
            
            pixel_area = np.count_nonzero(clean_m)
            
            if pixel_area >= 0.02 * (W * H):
                # Penalty: if touches frame border, heavily penalize
                penalty = border_c * 1000.0 if border_c > 10 else 0.0
                score = pixel_area - penalty
                scored_candidates.append({
                    "idx": idx,
                    "box": [bx1, by1, bx2, by2],
                    "area": pixel_area,
                    "border_contact": border_c,
                    "score": score,
                    "mask": clean_m
                })
                print(f"Cand {idx}: box={[bx1, by1, bx2, by2]}, area={pixel_area}, border_c={border_c} -> score={score}")

scored_candidates.sort(key=lambda x: x["score"], reverse=True)
winner = scored_candidates[0]
print(f"\nWINNER: Det {winner['idx']} with area={winner['area']}, border_contact={winner['border_contact']}, score={winner['score']}")

# 2. CROP WITH 10 PX MARGIN
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
crop_mask = stage1._apply_photometric_paper_gate(crop_bgr, crop_mask)
crop_mask = stage1._keep_largest_component(crop_mask)

vec = vectorizer.vectorize(crop_mask)
vis = crop_bgr.copy()
cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 2, cv2.LINE_AA)

cv2.imwrite("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/selected_castillo_white_features.png", vis)
print("Saved selected_castillo_white_features.png!")
