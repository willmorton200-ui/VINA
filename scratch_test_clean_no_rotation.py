import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/castillo_liria_pair.jpg"
img_bgr = cv2.imread(img_path)
H, W = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()

# 1. Run YOLO to get candidate masks
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
            if pixel_area >= 0.015 * (W * H):
                penalty = border_c * 1000.0 if border_c > 10 else 0.0
                score = pixel_area - penalty
                scored_candidates.append({
                    "idx": idx,
                    "box": [bx1, by1, bx2, by2],
                    "area": pixel_area,
                    "score": score,
                    "mask": clean_m
                })

scored_candidates.sort(key=lambda x: x["score"], reverse=True)
winner = scored_candidates[0]
print(f"Winner: Det {winner['idx']}, Area={winner['area']}, Score={winner['score']}")

# 2. SMOOTH MASK (no ragged / stepped notches)
win_mask = winner["mask"]
# Smooth mask boundary with morphological closing & opening
kernel_smooth = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
win_mask_smoothed = cv2.morphologyEx(win_mask, cv2.MORPH_CLOSE, kernel_smooth)
win_mask_smoothed = cv2.morphologyEx(win_mask_smoothed, cv2.MORPH_OPEN, kernel_smooth)

# 3. DIRECT CROP WITH 10 PX MARGIN IN ORIGINAL IMAGE SPACE (NO PRE-ROTATION!)
coords = cv2.findNonZero(win_mask_smoothed)
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
crop_mask = win_mask_smoothed[y1:y2, x1:x2].copy()

# 4. VECTORIZE DIRECTLY ON ORIGINAL CROP
vec = vectorizer.vectorize(crop_mask)

# 5. 3D COON'S PATCH REMAP DIRECTLY FROM ORIGINAL CROP (NO PRE-ROTATION BLUR!)
grid_rows, grid_cols = 24, 32
u_g = np.linspace(0.0, 1.0, grid_cols)
v_g = np.linspace(0.0, 1.0, grid_rows)
u_vals = np.linspace(0.0, 1.0, len(vec.T_curve))
v_vals = np.linspace(0.0, 1.0, len(vec.L_line))

T_res = np.column_stack((np.interp(u_g, u_vals, vec.T_curve[:, 0]), np.interp(u_g, u_vals, vec.T_curve[:, 1])))
B_res = np.column_stack((np.interp(u_g, u_vals, vec.B_curve[:, 0]), np.interp(u_g, u_vals, vec.B_curve[:, 1])))
L_res = np.column_stack((np.interp(v_g, v_vals, vec.L_line[:, 0]), np.interp(v_g, v_vals, vec.L_line[:, 1])))
R_res = np.column_stack((np.interp(v_g, v_vals, vec.R_line[:, 0]), np.interp(v_g, v_vals, vec.R_line[:, 1])))

u_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
v_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
h_c, w_c = crop_bgr.shape[:2]

for r in range(grid_rows):
    v_val = v_g[r]
    for c in range(grid_cols):
        u_val = u_g[c]
        c_blend = (1.0 - u_val)*(1.0 - v_val)*vec.P_TL + u_val*(1.0 - v_val)*vec.P_TR + (1.0 - u_val)*v_val*vec.P_BL + u_val*v_val*vec.P_BR
        pt = (1.0 - v_val)*T_res[c] + v_val*B_res[c] + (1.0 - u_val)*L_res[r] + u_val*R_res[r] - c_blend
        u_grid[r, c] = np.clip(pt[0], 0, w_c - 1)
        v_grid[r, c] = np.clip(pt[1], 0, h_c - 1)

arc_T = np.sum(np.hypot(np.diff(vec.T_curve[:, 0]), np.diff(vec.T_curve[:, 1])))
arc_B = np.sum(np.hypot(np.diff(vec.B_curve[:, 0]), np.diff(vec.B_curve[:, 1])))
dst_w = max(int(round(max(arc_T, arc_B))), 100)

len_L = np.sum(np.hypot(np.diff(vec.L_line[:, 0]), np.diff(vec.L_line[:, 1])))
len_R = np.sum(np.hypot(np.diff(vec.R_line[:, 0]), np.diff(vec.R_line[:, 1])))
dst_h = max(int(round(max(len_L, len_R))), 100)

map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
dewarped = cv2.remap(crop_bgr, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)

# OCR
ocr_dew = stage1.ocr_pipeline.process(dewarped) if hasattr(stage1, 'ocr_pipeline') else None

# Save diagnostics
vis = crop_bgr.copy()
cv2.polylines(vis, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis, [vec.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 2, cv2.LINE_AA)

cv2.imwrite("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/norotate_crop.png", crop_bgr)
cv2.imwrite("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/norotate_mask.png", crop_mask)
cv2.imwrite("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/norotate_features.png", vis)
cv2.imwrite("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/norotate_dewarped.png", dewarped)
print(f"Crop shape: {crop_bgr.shape[1]}x{crop_bgr.shape[0]}, Dewarped shape: {dewarped.shape[1]}x{dewarped.shape[0]}")
