import cv2
import numpy as np
import os
import easyocr

crop = cv2.imread(r"D:\VINA\outputs\test_michel_extreme\photo_2026-08-10_12-34-30 (2)\stage1_retinex.png")
mask = cv2.imread(r"D:\VINA\outputs\test_michel_extreme\photo_2026-08-10_12-34-30 (2)\stage1_mask.png", cv2.IMREAD_GRAYSCALE)
dewarp = cv2.imread(r"D:\VINA\outputs\test_michel_extreme\photo_2026-08-10_12-34-30 (2)\flattened_image.png")
mesh_vis = cv2.imread(r"D:\VINA\outputs\test_michel_extreme\photo_2026-08-10_12-34-30 (2)\stage3_mesh.png")

from pipeline.vectorizer import MaskVectorizer
vec = MaskVectorizer()
vm = vec.vectorize(mask)

P_TL = vm.P_TL
P_TR = vm.P_TR
P_BL = vm.P_BL
P_BR = vm.P_BR

# 1. Semitransparent Greenish Mask Overlay on Crop
vis = crop.copy()
mask_2d = mask > 127
green_layer = crop.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Blue Side lines along extreme left and right
cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green curves along extreme top and bottom
cv2.polylines(vis, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)

# Red central axis
p_top_mid = (P_TL + P_TR) / 2.0
p_bot_mid = (P_BL + P_BR) / 2.0
for s in range(0, int(np.linalg.norm(p_bot_mid - p_top_mid)), 14):
    v_s = s / float(np.linalg.norm(p_bot_mid - p_top_mid))
    pt_a = (1.0 - v_s) * p_top_mid + v_s * p_bot_mid
    cv2.line(vis, (int(pt_a[0]), int(pt_a[1])), (int(pt_a[0]), int(pt_a[1] + 7)), (0, 0, 255), 2, cv2.LINE_AA)

# 4 Corner Green Dots
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
out_overlay = os.path.join(artifacts_dir, "michel_extreme_greenish_overlay.png")
cv2.imwrite(out_overlay, vis)

out_mesh = os.path.join(artifacts_dir, "michel_extreme_mesh.png")
cv2.imwrite(out_mesh, mesh_vis)

out_dewarp = os.path.join(artifacts_dir, "michel_extreme_dewarped.png")
cv2.imwrite(out_dewarp, dewarp)

# OCR
reader = easyocr.Reader(['ru', 'en'], gpu=True)
ocr_res = reader.readtext(dewarp)
vis_ocr = dewarp.copy()
ocr_res.sort(key=lambda r: min(p[1] for p in r[0]))

for idx, (bbox, text, conf) in enumerate(ocr_res, start=1):
    pts = np.array(bbox, dtype=np.int32)
    x_min, y_min = np.min(pts, axis=0)
    x_max, y_max = np.max(pts, axis=0)
    clean_text = text.strip()
    if clean_text:
        cv2.polylines(vis_ocr, [pts], isClosed=True, color=(0, 255, 0), thickness=2, lineType=cv2.LINE_AA)
        label_str = f"{clean_text} ({conf*100.0:.0f}%)"
        (t_w, t_h), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y = max(y_min - 4, t_h + 4)
        cv2.rectangle(vis_ocr, (x_min, tag_y - t_h - 2), (x_min + t_w + 6, tag_y + 2), (0, 0, 0), -1)
        cv2.putText(vis_ocr, label_str, (x_min + 3, tag_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

out_ocr = os.path.join(artifacts_dir, "michel_extreme_ocr.png")
cv2.imwrite(out_ocr, vis_ocr)

print("P_TL:", P_TL)
print("P_TR:", P_TR)
print("P_BL:", P_BL)
print("P_BR:", P_BR)
print("Saved all Michel Schneider extreme vector artifacts successfully!")
