import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage5_ocr import Stage5OCRDecoder
from pipeline.wine_lexicon_corrector import WineVocabularyCorrector

img_path = "d:/VINA/test_dataset/butilki/monastyrskaya_izba.jpg"
img_bgr = cv2.imread(img_path)
h_orig, w_orig = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()
stage5 = Stage5OCRDecoder(use_gpu=True)
lexicon = WineVocabularyCorrector()

# Crop Det 0 (Monastyrskaya Izba)
bx1, by1, bx2, by2 = 374, 471, 654, 890
pad = 20
crop_bgr = img_bgr[max(0, by1-pad):min(h_orig, by2+pad), max(0, bx1-pad):min(w_orig, bx2+pad)].copy()

# Segment mask
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.20)
m_raw = yolo_res[0].masks.data[0].cpu().numpy()
mask_full = (cv2.resize(m_raw, (w_orig, h_orig)) > 0.5).astype(np.uint8) * 255
mask_crop = mask_full[max(0, by1-pad):min(h_orig, by2+pad), max(0, bx1-pad):min(w_orig, bx2+pad)].copy()
mask_crop = stage1._apply_photometric_paper_gate(crop_bgr, mask_crop)
mask_crop = stage1._keep_largest_component(mask_crop)

# 1. OCR on RAW CROP (no transformation)
ocr_raw = stage5.process(crop_bgr)
print("=== OCR ON RAW CROP (NO DEWARP) ===")
print("Raw Words:", ocr_raw["num_words"])
print("Raw Full Text:\n", ocr_raw["full_text"])
print("Raw Tokens:\n", [t["text"] for t in ocr_raw["text_blocks"]])

# 2. Vectorize
vec = vectorizer.vectorize(mask_crop)

# 3. 3D Coon's grid & Dewarp
grid_rows, grid_cols = 24, 32
u_g = np.linspace(0.0, 1.0, grid_cols)
v_g = np.linspace(0.0, 1.0, grid_rows)
u_vals = np.linspace(0.0, 1.0, len(vec.T_curve))
v_vals = np.linspace(0.0, 1.0, len(vec.L_line))

T_res = np.column_stack((np.interp(u_g, u_vals, vec.T_curve[:, 0]), np.interp(u_g, u_vals, vec.T_curve[:, 1])))
B_res = np.column_stack((np.interp(u_g, u_vals, vec.B_curve[:, 0]), np.interp(u_g, u_vals, vec.B_curve[:, 1])))
L_res = np.column_stack((np.interp(v_g, v_vals, vec.L_line[:, 0]), np.interp(v_g, v_vals, vec.L_line[:, 1])))
R_res = np.column_stack((np.interp(v_g, v_vals, vec.R_line[:, 0]), np.interp(v_g, v_vals, vec.R_line[:, 1])))

cw, ch = crop_bgr.shape[1], crop_bgr.shape[0]
u_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
v_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
for r in range(grid_rows):
    v_val = v_g[r]
    for c in range(grid_cols):
        u_val = u_g[c]
        c_blend = (1.0 - u_val)*(1.0 - v_val)*vec.P_TL + u_val*(1.0 - v_val)*vec.P_TR + (1.0 - u_val)*v_val*vec.P_BL + u_val*v_val*vec.P_BR
        pt = (1.0 - v_val)*T_res[c] + v_val*B_res[c] + (1.0 - u_val)*L_res[r] + u_val*R_res[r] - c_blend
        u_grid[r, c] = np.clip(pt[0], 0, cw - 1)
        v_grid[r, c] = np.clip(pt[1], 0, ch - 1)

arc_T = np.sum(np.hypot(np.diff(vec.T_curve[:, 0]), np.diff(vec.T_curve[:, 1])))
arc_B = np.sum(np.hypot(np.diff(vec.B_curve[:, 0]), np.diff(vec.B_curve[:, 1])))
dst_w = max(int(round(max(arc_T, arc_B))), 100)

len_L = np.sum(np.hypot(np.diff(vec.L_line[:, 0]), np.diff(vec.L_line[:, 1])))
len_R = np.sum(np.hypot(np.diff(vec.R_line[:, 0]), np.diff(vec.R_line[:, 1])))
dst_h = max(int(round(max(len_L, len_R))), 100)

map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
dewarped = cv2.remap(crop_bgr, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)

ocr_dew = stage5.process(dewarped)
print("\n=== OCR ON DEWARPED SCAN ===")
print("Dewarped Words:", ocr_dew["num_words"])
print("Dewarped Full Text:\n", ocr_dew["full_text"])
print("Dewarped Tokens:\n", [t["text"] for t in ocr_dew["text_blocks"]])

# Save visual debug
cv2.imwrite("scratch_debug/monastyrskaya_crop.png", crop_bgr)
cv2.imwrite("scratch_debug/monastyrskaya_dewarped.png", dewarped)
