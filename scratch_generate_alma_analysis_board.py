import cv2
import numpy as np
import os
import matplotlib.pyplot as plt

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer
from pipeline.dewarp_engine import CylindricalDewarpEngine

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

# 1. Old Flawed Mask (without corner prompts)
sam_old = SAMRefiner(model_type="vit_h")
box0 = [191, 700, 903, 2197]
bx1, by1, bx2, by2 = box0
bw, bh = bx2 - bx1, by2 - by1

# Predict with ONLY box
pad_x = int(bw * 0.25)
pad_y = int(bh * 0.25)
rx1, ry1 = max(0, bx1 - pad_x), max(0, by1 - pad_y)
rx2, ry2 = min(w, bx2 + pad_x), min(h, by2 + pad_y)
roi_bgr = img_bgr[ry1:ry2, rx1:rx2].copy()
roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)
sam_old.predictor.set_image(roi_rgb)

local_box = np.array([bx1 - rx1, by1 - ry1, bx2 - rx1, by2 - ry1], dtype=np.float32)
masks_old, scores_old, _ = sam_old.predictor.predict(
    box=local_box[None, :],
    multimask_output=False
)
mask_old_roi = masks_old[0].astype(np.uint8) * 255
full_mask_old = np.zeros((h, w), dtype=np.uint8)
full_mask_old[ry1:ry2, rx1:rx2] = mask_old_roi

# Crop old
coords_old = cv2.findNonZero(full_mask_old)
ox1 = max(0, int(np.min(coords_old[:, 0, 0])) - 10)
oy1 = max(0, int(np.min(coords_old[:, 0, 1])) - 10)
ox2 = min(w, int(np.max(coords_old[:, 0, 0])) + 11)
oy2 = min(h, int(np.max(coords_old[:, 0, 1])) + 11)
crop_old_bgr = img_bgr[oy1:oy2, ox1:ox2].copy()
crop_old_mask = full_mask_old[oy1:oy2, ox1:ox2].copy()

vec = MaskVectorizer()
vec_old = vec.vectorize(crop_old_mask)

vis_old = crop_old_bgr.copy()
cv2.polylines(vis_old, [vec_old.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_old, [vec_old.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_old, [vec_old.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_old, [vec_old.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec_old.P_TL, vec_old.P_TR, vec_old.P_BL, vec_old.P_BR]:
    cv2.circle(vis_old, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_old, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)

# 2. New 5-Point Guided SAM Mask
margin_x = int(bw * 0.06)
margin_y = int(bh * 0.06)
pts_prompt = np.array([
    [bx1 + margin_x - rx1, by1 + margin_y - ry1],
    [bx2 - margin_x - rx1, by1 + margin_y - ry1],
    [bx1 + margin_x - rx1, by2 - margin_y - ry1],
    [bx2 - margin_x - rx1, by2 - margin_y - ry1],
    [(bx1 + bx2) // 2 - rx1, (by1 + by2) // 2 - ry1]
], dtype=np.float32)
labels_prompt = np.array([1, 1, 1, 1, 1], dtype=np.int32)

masks_new, scores_new, _ = sam_old.predictor.predict(
    point_coords=pts_prompt,
    point_labels=labels_prompt,
    box=local_box[None, :],
    multimask_output=True
)
best_idx = np.argmax(scores_new)
mask_new_roi = masks_new[best_idx].astype(np.uint8) * 255
full_mask_new = np.zeros((h, w), dtype=np.uint8)
full_mask_new[ry1:ry2, rx1:rx2] = mask_new_roi

# Crop new
coords_new = cv2.findNonZero(full_mask_new)
nx1 = max(0, int(np.min(coords_new[:, 0, 0])) - 10)
ny1 = max(0, int(np.min(coords_new[:, 0, 1])) - 10)
nx2 = min(w, int(np.max(coords_new[:, 0, 0])) + 11)
ny2 = min(h, int(np.max(coords_new[:, 0, 1])) + 11)
crop_new_bgr = img_bgr[ny1:ny2, nx1:nx2].copy()
crop_new_mask = full_mask_new[ny1:ny2, nx1:nx2].copy()

vec_new = vec.vectorize(crop_new_mask)

vis_new = crop_new_bgr.copy()
cv2.polylines(vis_new, [vec_new.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_new, [vec_new.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_new, [vec_new.T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis_new, [vec_new.B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for pt in [vec_new.P_TL, vec_new.P_TR, vec_new.P_BL, vec_new.P_BR]:
    cv2.circle(vis_new, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_new, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)

# Draw prompt anchor stars
for pt in pts_prompt:
    cv2.drawMarker(vis_new, (int(pt[0] + rx1 - nx1), int(pt[1] + ry1 - ny1)), (0, 255, 255), cv2.MARKER_STAR, 18, 2, cv2.LINE_AA)

# Build a clear 4-panel comparison figure
fig, axes = plt.subplots(1, 4, figsize=(20, 10))

axes[0].imshow(cv2.cvtColor(crop_old_mask, cv2.COLOR_BGR2RGB))
axes[0].set_title("1. ОШИБКА: Маска с выгрызами\n(SAM сжался по силуэту грифона)", fontsize=11, color="red")
axes[0].axis("off")

axes[1].imshow(cv2.cvtColor(vis_old, cv2.COLOR_BGR2RGB))
axes[1].set_title("2. СЛЕДСТВИЕ: Углы P_TL/P_TR упали\nв выгрыз под грифоном (y=494)", fontsize=11, color="red")
axes[1].axis("off")

axes[2].imshow(cv2.cvtColor(crop_new_mask, cv2.COLOR_BGR2RGB))
axes[2].set_title("3. ИСПРАВЛЕНИЕ: 5 якорных точек\n(Монолитная маска прямоугольника)", fontsize=11, color="green")
axes[2].axis("off")

axes[3].imshow(cv2.cvtColor(vis_new, cv2.COLOR_BGR2RGB))
axes[3].set_title("4. ИТОГ: Точные 4 угла на срезах бумаги,\nгладкие направляющие цилиндра", fontsize=11, color="green")
axes[3].axis("off")

plt.tight_layout()
os.makedirs("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97", exist_ok=True)
board_path = "C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/alma_reserve_segmentation_analysis_board.png"
plt.savefig(board_path, dpi=150, bbox_inches="tight")
plt.close()

print(f"Comparison board generated at: {board_path}")
