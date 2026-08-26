import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR
import easyocr

class EnhancedOCRDecoder:
    def __init__(self, use_gpu=True):
        self.rapid_ocr = RapidOCR()
        self.easy_ru = easyocr.Reader(['ru'], gpu=use_gpu)
        self.easy_en = easyocr.Reader(['en'], gpu=use_gpu)

    def extract_text(self, img_bgr: np.ndarray) -> list[dict]:
        h, w = img_bgr.shape[:2]
        
        # 1. Image Enhancement (Upscale + CLAHE + Sharpening)
        scale = 1.5 if max(h, w) < 1200 else 1.0
        if scale > 1.0:
            img_proc = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LANCZOS4)
        else:
            img_proc = img_bgr.copy()

        # CLAHE Contrast
        lab = cv2.cvtColor(img_proc, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enh = clahe.apply(l)
        img_enh = cv2.cvtColor(cv2.merge([l_enh, a, b]), cv2.COLOR_LAB2BGR)

        # 2. Primary High-Fidelity OCR via RapidOCR
        rapid_results, _ = self.rapid_ocr(img_enh)
        text_blocks = []

        if rapid_results:
            for bbox, text, conf in rapid_results:
                pts = np.array(bbox, dtype=np.float64) / scale
                x_min, y_min = np.min(pts, axis=0)
                x_max, y_max = np.max(pts, axis=0)
                clean_text = text.strip()
                if clean_text and float(conf) > 0.35:
                    text_blocks.append({
                        "text": clean_text,
                        "confidence": round(float(conf), 3),
                        "bbox": [[int(p[0]), int(p[1])] for p in pts],
                        "rect": {"x": int(x_min), "y": int(y_min), "w": int(x_max - x_min), "h": int(y_max - y_min)}
                    })

        # 3. If Cyrillic words look suspicious (transliterated), verify with EasyOCR (ru)
        cyrillic_chars = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
        easy_ru_results = self.easy_ru.readtext(cv2.cvtColor(img_enh, cv2.COLOR_BGR2RGB))
        for bbox, text, conf in easy_ru_results:
            clean_text = text.strip()
            # If genuine Cyrillic word with high confidence
            has_cyr = sum(c in cyrillic_chars for c in clean_text) >= 2
            if has_cyr and float(conf) > 0.60:
                pts = np.array(bbox, dtype=np.float64) / scale
                x_min, y_min = np.min(pts, axis=0)
                x_max, y_max = np.max(pts, axis=0)
                
                # Check overlap with existing blocks
                matched = False
                for b in text_blocks:
                    bx, by, bw, bh = b["rect"]["x"], b["rect"]["y"], b["rect"]["w"], b["rect"]["h"]
                    # Intersection over Union
                    ix1, iy1 = max(x_min, bx), max(y_min, by)
                    ix2, iy2 = min(x_max, bx + bw), min(y_max, by + bh)
                    if ix2 > ix1 and iy2 > iy1:
                        inter_area = (ix2 - ix1) * (iy2 - iy1)
                        union_area = (x_max - x_min) * (y_max - y_min) + bw * bh - inter_area
                        if inter_area / max(union_area, 1.0) > 0.3:
                            # Replace if EasyOCR has higher confidence for Cyrillic
                            b["text"] = clean_text
                            b["confidence"] = max(b["confidence"], round(float(conf), 3))
                            matched = True
                            break
                if not matched:
                    text_blocks.append({
                        "text": clean_text,
                        "confidence": round(float(conf), 3),
                        "bbox": [[int(p[0]), int(p[1])] for p in pts],
                        "rect": {"x": int(x_min), "y": int(y_min), "w": int(x_max - x_min), "h": int(y_max - y_min)}
                    })

        # Sort top to bottom
        text_blocks.sort(key=lambda b: (b["rect"]["y"], b["rect"]["x"]))
        return text_blocks

# Test on Michel Schneider
ocr_decoder = EnhancedOCRDecoder(use_gpu=True)
img = cv2.imread(r"D:\VINA\outputs\test_michel_extreme\photo_2026-08-10_12-34-30 (2)\flattened_image.png")
results = ocr_decoder.extract_text(img)

print("\n" + "="*50)
print("     ENHANCED HYBRID OCR ON MICHEL SCHNEIDER")
print("="*50)
for idx, b in enumerate(results, 1):
    print(f"[{idx:02d}] {b['text']:<35} | Точность: {b['confidence']*100.0:5.1f}%")
print("="*50)
