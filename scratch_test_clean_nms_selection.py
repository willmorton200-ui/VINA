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
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.25, iou=0.45)
masks_data = yolo_res[0].masks.data.cpu().numpy()
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()

valid_labels = []
for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs)):
    cls_int = int(cls_id)
    cls_name = stage1.yolo_model.names.get(cls_int, f"class_{cls_int}").lower()
    
    if cls_int == 0 or "label" in cls_name:
        bx1, by1, bx2, by2 = [int(v) for v in box]
        bw, bh = bx2 - bx1, by2 - by1
        aspect_ratio = bw / float(bh)
        
        # Must have realistic single bottle label aspect ratio
        if 0.40 <= aspect_ratio <= 1.25 and bw <= 0.60 * W and bh <= 0.70 * H:
            m_raw = masks_data[idx]
            m_full = (cv2.resize(m_raw, (W, H)) > 0.5).astype(np.uint8) * 255
            
            # Boundary contact check (Rule 1: Exclude if touches frame by > 10 px)
            top_contact = np.count_nonzero(m_full[0, :])
            bot_contact = np.count_nonzero(m_full[H - 1, :])
            left_contact = np.count_nonzero(m_full[:, 0])
            right_contact = np.count_nonzero(m_full[:, W - 1])
            border_contact = top_contact + bot_contact + left_contact + right_contact
            
            if border_contact <= 10:
                clean_m = stage1._keep_largest_component(m_full)
                area = np.count_nonzero(clean_m)
                valid_labels.append({
                    "idx": idx,
                    "box": [bx1, by1, bx2, by2],
                    "area": area,
                    "conf": float(conf),
                    "mask": clean_m
                })
                print(f"Valid label Det {idx}: box={[bx1, by1, bx2, by2]}, area={area}, conf={conf:.2f}")
            else:
                print(f"Excluded truncated Det {idx}: box={[bx1, by1, bx2, by2]}, border_contact={border_contact}")

valid_labels.sort(key=lambda x: x["area"], reverse=True)
winner = valid_labels[0]
print(f"\n---> WINNER SELECTED BY LARGEST AREA: Det {winner['idx']} with area={winner['area']} (box={winner['box']})")

# 2. TIGHT CROP WITH 10 PX MARGIN WITHOUT CUTTING EDGES
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

# Paper gate
crop_mask = stage1._apply_photometric_paper_gate(crop_bgr, crop_mask)
crop_mask = stage1._keep_largest_component(crop_mask)

# Check bounds inside crop to verify 10px margin on all sides
c_check = cv2.findNonZero(crop_mask)
mx_min = int(np.min(c_check[:, 0, 0]))
mx_max = int(np.max(c_check[:, 0, 0]))
my_min = int(np.min(c_check[:, 0, 1]))
my_max = int(np.max(c_check[:, 0, 1]))

print(f"Crop dimensions: {crop_bgr.shape[1]}x{crop_bgr.shape[0]}")
print(f"Actual margins inside crop: Left={mx_min}px, Right={crop_bgr.shape[1]-mx_max-1}px, Top={my_min}px, Bottom={crop_bgr.shape[0]-my_max-1}px")

vec = vectorizer.vectorize(crop_mask)
vis = crop_bgr.copy()
cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 2, cv2.LINE_AA)

cv2.imwrite("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/perfect_castillo_white_crop_features.png", vis)
cv2.imwrite("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/perfect_castillo_white_crop_mask.png", crop_mask)
print("Saved perfect_castillo_white_crop_features.png!")
