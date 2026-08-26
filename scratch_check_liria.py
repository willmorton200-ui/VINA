import cv2
import numpy as np
import os

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

p1 = Stage1Preprocessor()
res_s1 = p1.process(img_bgr)

crop_bgr = res_s1["cropped_bgr"]
crop_mask = res_s1["mask"]
vm = res_s1.get("vector_mask")

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
os.makedirs(artifacts_dir, exist_ok=True)

# 1. Semitransparent Green Overlay on Crop
vis_overlay = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis_overlay[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Draw Vector Mask
if vm is not None:
    P_TL = vm.P_TL
    P_TR = vm.P_TR
    P_BL = vm.P_BL
    P_BR = vm.P_BR
    print("Vector Mask Corners:")
    print("  P_TL:", P_TL)
    print("  P_TR:", P_TR)
    print("  P_BL:", P_BL)
    print("  P_BR:", P_BR)

    # Blue lateral lines
    cv2.line(vis_overlay, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
    cv2.line(vis_overlay, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

    # Green top and bottom curves
    if vm.T_curve is not None:
        cv2.polylines(vis_overlay, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    if vm.B_curve is not None:
        cv2.polylines(vis_overlay, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_overlay, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

cv2.imwrite(os.path.join(artifacts_dir, "liria_check_stage1_overlay.png"), vis_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "liria_check_stage1_mask.png"), crop_mask)
cv2.imwrite(os.path.join(artifacts_dir, "liria_check_stage1_crop.png"), crop_bgr)

# Let's also run Stage 2, 3, 4, 5 and check the 3D mesh and dewarped image!
from pipeline.stage2_features import Stage2FeatureExtractor
from pipeline.stage3_optimization import Stage3CylinderOptimizer
from pipeline.stage4_remapping import Stage4Remapper

s2 = Stage2FeatureExtractor()
res_s2 = s2.process(res_s1["binarized"], res_s1["enhanced_bgr"], mask=crop_mask, vector_mask=vm)

s3 = Stage3CylinderOptimizer()
res_s3 = s3.process(crop_bgr, res_s2["text_lines"], res_s2["line_segments"], res_s2["cam_orientation"], crop_mask, label_boundaries=res_s2.get("label_boundaries"))

s4 = Stage4Remapper(interpolation_mode="lanczos")
res_s4 = s4.process(crop_bgr, res_s3)

cv2.imwrite(os.path.join(artifacts_dir, "liria_check_mesh.png"), res_s3["mesh_vis_bgr"])
cv2.imwrite(os.path.join(artifacts_dir, "liria_check_dewarped.png"), res_s4["dewarped_bgr"])

print("Saved all liria check artifacts successfully!")
