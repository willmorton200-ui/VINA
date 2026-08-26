import cv2
import numpy as np
import os
from pipeline.dewarp_engine import CylindricalDewarpEngine

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

engine = CylindricalDewarpEngine(use_gpu=True)
res = engine.process_image(img_bgr)

p1_res = engine.stage1.process(img_bgr)
cropped_bgr = p1_res["cropped_bgr"]
mask = p1_res["mask"]
vm = p1_res["vector_mask"]

print("=== ВЕКТОРИЗАЦИЯ ПО 3 ШАГАМ ===")
print(f"  P_TL = [{vm.P_TL[0]:.1f}, {vm.P_TL[1]:.1f}]")
print(f"  P_TR = [{vm.P_TR[0]:.1f}, {vm.P_TR[1]:.1f}]")
print(f"  P_BL = [{vm.P_BL[0]:.1f}, {vm.P_BL[1]:.1f}]")
print(f"  P_BR = [{vm.P_BR[0]:.1f}, {vm.P_BR[1]:.1f}]")

# Render overlay
vis = cropped_bgr.copy()
mask_2d = mask > 127
green_layer = cropped_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(cropped_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Lateral tangents (Orange)
cv2.polylines(vis, [vm.L_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vm.R_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)

# Top & Bottom Semi-Ellipses (Green)
cv2.polylines(vis, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

# Intersection Points (White/Red Circles)
for pt in [vm.P_TL, vm.P_TR, vm.P_BL, vm.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 10, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "castillo_step123_verified_overlay.png"), vis)

# Pipeline Mesh & Dewarped
p2_res = engine.stage2.process(cropped_bgr, p1_res["enhanced_bgr"], mask=mask)
p3_res = engine.stage3.process(cropped_bgr, p2_res["text_lines"], p2_res["line_segments"], p2_res["cam_orientation"], mask, label_boundaries=p2_res.get("label_boundaries"))
cv2.imwrite(os.path.join(artifacts_dir, "castillo_step123_verified_mesh.png"), p3_res["vis_mesh"])

p4_res = engine.stage4.process(cropped_bgr, p3_res)
p5_res = engine.stage5.process(p4_res["dewarped_bgr"])
cv2.imwrite(os.path.join(artifacts_dir, "castillo_step123_verified_dewarped.png"), p4_res["dewarped_bgr"])
cv2.imwrite(os.path.join(artifacts_dir, "castillo_step123_verified_annotated.png"), p5_res["annotated_bgr"])

print(f"\nRecognized Text: {p5_res['full_text']}")
print("Saved all step 1-2-3 verified artifacts successfully!")
