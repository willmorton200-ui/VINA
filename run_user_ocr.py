import cv2
import numpy as np
import easyocr
import json

# Load dewarped image
img_path = r"D:\VINA\outputs\test_exact_mask_pipeline\photo_2026-08-11_21-10-16\flattened_image.png"
img_bgr = cv2.imread(img_path)
if img_bgr is None:
    img_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\exact_vector_flattened_image.png"
    img_bgr = cv2.imread(img_path)

h, w = img_bgr.shape[:2]

# Initialize EasyOCR (Russian + English, GPU)
print("Initializing OCR engine (ru + en) on GPU...")
reader = easyocr.Reader(['ru', 'en'], gpu=True)

# Image enhancements for optimal OCR:
# 1. CLAHE Contrast boost on luminance
lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
l, a, b = cv2.split(lab)
clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
l_enhanced = clahe.apply(l)
enhanced_rgb = cv2.cvtColor(cv2.merge([l_enhanced, a, b]), cv2.COLOR_LAB2RGB)

print("Running OCR on rectified dewarped label...")
results = reader.readtext(enhanced_rgb, paragraph=False)

print("\n" + "="*50)
print("             OCR РЕЗУЛЬТАТЫ РАСПОЗНАВАНИЯ")
print("="*50)

ocr_tokens = []
vis_annotated = img_bgr.copy()

# Sort results by vertical position (top to bottom)
results.sort(key=lambda r: min(p[1] for p in r[0]))

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
            "bbox": [[int(p[0]), int(p[1])] for p in bbox],
            "box": [int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)]
        })
        print(f"[{idx:02d}] {clean_text:<30} | Точность: {conf*100.0:5.1f}%")

        # Draw green bounding box on image
        cv2.polylines(vis_annotated, [pts], isClosed=True, color=(0, 255, 0), thickness=2, lineType=cv2.LINE_AA)
        
        # Label background pill
        label_str = f"{idx}. {clean_text} ({conf*100.0:.0f}%)"
        (t_w, t_h), _ = cv2.getTextSize(label_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        tag_y = max(y_min - 6, t_h + 4)
        cv2.rectangle(vis_annotated, (x_min, tag_y - t_h - 4), (x_min + t_w + 8, tag_y + 4), (0, 0, 0), -1)
        cv2.rectangle(vis_annotated, (x_min, tag_y - t_h - 4), (x_min + t_w + 8, tag_y + 4), (0, 255, 0), 1)
        cv2.putText(vis_annotated, label_str, (x_min + 4, tag_y - 1), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

print("="*50)

# Save annotated image
out_annotated = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\ocr_recognized_annotated.png"
cv2.imwrite(out_annotated, vis_annotated)

# Save JSON results
out_json = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\ocr_results.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(ocr_tokens, f, ensure_ascii=False, indent=2)

print(f"\nSaved annotated image to: {out_annotated}")
print(f"Saved OCR JSON to: {out_json}")
