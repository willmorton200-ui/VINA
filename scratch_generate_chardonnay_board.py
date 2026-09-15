import cv2
import numpy as np
import os
import matplotlib.pyplot as plt

from pipeline.dewarp_engine import CylindricalDewarpEngine
from pipeline.stage1_preprocessing import Stage1Preprocessor

engine = CylindricalDewarpEngine()
img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-12.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
crop_bgr, crop_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)

res = engine._dewarp_single_tier(crop_bgr, crop_mask)

vis_features = res["vis_features"]
dewarped = res["dewarped"]

fig, axes = plt.subplots(1, 4, figsize=(22, 10))

axes[0].imshow(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
axes[0].set_title("1. Исходный снимок на полке\n(Центральная бутылка в фокусе)", fontsize=11)
axes[0].axis("off")

axes[1].imshow(cv2.cvtColor(crop_mask, cv2.COLOR_BGR2RGB))
axes[1].set_title("2. Точная маска SAM ViT-H\n(Монолитный прямоугольник)", fontsize=11, color="green")
axes[1].axis("off")

axes[2].imshow(cv2.cvtColor(vis_features, cv2.COLOR_BGR2RGB))
axes[2].set_title("3. 4 угла и направляющие цилиндра\n(P_TL=[34,41], P_TR=[676,52])", fontsize=11, color="green")
axes[2].axis("off")

axes[3].imshow(cv2.cvtColor(dewarped, cv2.COLOR_BGR2RGB))
axes[3].set_title(f"4. Выпрямленный плоский скан\nOCR: ALMA VALLEY RESERVE 2022 CHARDONNAY", fontsize=11, color="green")
axes[3].axis("off")

plt.tight_layout()
os.makedirs("C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97", exist_ok=True)
board_path = "C:/Users/User/.gemini/antigravity-ide/brain/982dbb9e-4780-4467-a511-0a784bef8b97/alma_chardonnay_segmentation_analysis_board.png"
plt.savefig(board_path, dpi=150, bbox_inches="tight")
plt.close()

print(f"Comparison board generated at: {board_path}")
