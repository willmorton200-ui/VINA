import cv2
import numpy as np
import easyocr
import json

# Paths
crop_path = r"D:\VINA\outputs\test_bottle_21_10_04\photo_2026-08-11_21-10-04\stage1_retinex.png"
mask_path = r"D:\VINA\outputs\test_bottle_21_10_04\photo_2026-08-11_21-10-04\stage1_mask.png"
dewarp_path = r"D:\VINA\outputs\test_bottle_21_10_04\photo_2026-08-11_21-10-04\flattened_image.png"

crop = cv2.imread(crop_path)
mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
dewarp = cv2.imread(dewarp_path)

h, w = mask.shape[:2]

# 1. Vectorize Mask Corners
from pipeline.vectorizer import MaskVectorizer
vec = MaskVectorizer()
vm = vec.vectorize(mask)

P_TL = vm.P_TL
P_TR = vm.P_TR
P_BL = vm.P_BL
P_BR = vm.P_BR

# 2. Render Semitransparent Greenish Mask Overlay on Crop
vis = crop.copy()
mask_bool = mask > 127
green_layer = np.zeros_like(vis)
green_layer[mask_bool] = [40, 225, 60]

alpha = 0.35
vis[mask_bool] = cv2.addWeighted(crop[mask_bool], 1.0 - alpha, green_layer[mask_bool], alpha, 0)

# Blue Side lines
cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green curves
cv2.polylines(vis, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)

# Central axis
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

out_greenish = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\new_bottle_greenish_overlay.png"
cv2.imwrite(out_greenish, vis)

# 3. High-Precision OCR on Flattened Dewarp Image
reader = easyocr.Reader(['ru', 'en'], gpu=True)
results = reader.readtext(dewarp)

vis_ocr = dewarp.copy()
ocr_tokens = []
for idx, (bbox, text, conf) in enumerate(results, start=1):
    pts = np.array(bbox, dtype=np.int32)
    x_min, y_min = np.min(pts, axis=0)
    x_max, y_max = np.max(pts, axis=0)
    clean_text = text.strip()
    if clean_text:
        ocr_tokens.append({
            "id": idx,
            "text": clean_text,
            "confidence": round(float(conf) * 100.0, 1),
            "bbox": [[int(p[0]), int(p[1])] for p in bbox]
        })
        cv2.polylines(vis_ocr, [pts], isClosed=True, color=(0, 255, 0), thickness=2, lineType=cv2.LINE_AA)
        label_str = f"{clean_text} ({conf*100.0:.0f}%)"
        (t_w, t_h), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y = max(y_min - 4, t_h + 4)
        cv2.rectangle(vis_ocr, (x_min, tag_y - t_h - 2), (x_min + t_w + 6, tag_y + 2), (0, 0, 0), -1)
        cv2.putText(vis_ocr, label_str, (x_min + 3, tag_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1, cv2.LINE_AA)

out_ocr = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\new_bottle_ocr_annotated.png"
cv2.imwrite(out_ocr, vis_ocr)

out_json = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\new_bottle_ocr_results.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(ocr_tokens, f, ensure_ascii=False, indent=2)

print("Saved new bottle report artifacts successfully!")
print(f"Recognized text tokens: {len(ocr_tokens)}")
for t in ocr_tokens:
    print(f"  - {t['text']} ({t['confidence']}%)")
