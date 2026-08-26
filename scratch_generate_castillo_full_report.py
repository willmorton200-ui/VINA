import cv2
import numpy as np
import os
from pipeline.dewarp_engine import CylindricalDewarpEngine

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

engine = CylindricalDewarpEngine(use_gpu=True)
artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"

# Extract Stage 1 outputs directly
p1_res = engine.stage1.process(img_bgr)
cropped_bgr = p1_res["cropped_bgr"]
clean_mask = p1_res["mask"]
enhanced_bgr = p1_res["enhanced_bgr"]
vector_mask = p1_res["vector_mask"]

# 2. Stage 2 Vector Overlay
vis_vector = cropped_bgr.copy()
mask_2d = clean_mask > 127
green_layer = cropped_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis_vector[mask_2d] = cv2.addWeighted(cropped_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Lateral polylines (Orange)
cv2.polylines(vis_vector, [vector_mask.L_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_vector, [vector_mask.R_line.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA)
# Top & Bottom Curves (Green)
cv2.polylines(vis_vector, [vector_mask.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis_vector, [vector_mask.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
# Corner Points
for pt in [vector_mask.P_TL, vector_mask.P_TR, vector_mask.P_BL, vector_mask.P_BR]:
    cv2.circle(vis_vector, (int(pt[0]), int(pt[1])), 10, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_vector, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

# 3. Stage 3 Mesh
p2_res = engine.stage2.process(cropped_bgr, enhanced_bgr, mask=clean_mask)
p3_res = engine.stage3.process(cropped_bgr, p2_res["text_lines"], p2_res["line_segments"], p2_res["cam_orientation"], clean_mask, label_boundaries=p2_res.get("label_boundaries"))
mesh_vis = p3_res["vis_mesh"]

# 4. Stage 4 Dewarped
p4_res = engine.stage4.process(cropped_bgr, p3_res)
dewarped_bgr = p4_res["dewarped_bgr"]

# 5. Stage 5 OCR
p5_res = engine.stage5.process(dewarped_bgr)
annotated_bgr = p5_res["annotated_bgr"]

# Save all high-res artifact images
cv2.imwrite(os.path.join(artifacts_dir, "castillo_report_1_mask.png"), clean_mask)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_report_2_vector.png"), vis_vector)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_report_3_mesh.png"), mesh_vis)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_report_4_dewarped.png"), dewarped_bgr)
cv2.imwrite(os.path.join(artifacts_dir, "castillo_report_5_ocr.png"), annotated_bgr)

print("Saved all Castillo de Liria report images successfully!")
print(f"Recognized text: {p5_res['full_text']}")
