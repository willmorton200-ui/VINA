"""
Stage 5: Character Recognition & Code Decoding
- High-Fidelity Multi-lingual OCR Engine (RapidOCR PP-OCRv4 + EasyOCR Russian Refinement)
- CLAHE + Lanczos-4 Super-Resolution Text Contrast Enhancement
- Graphical code decoding (Barcodes, QR Codes via OpenCV & pyzbar)
- Extraction of structured text blocks, coordinates, confidence scores
- Visual bounding box annotations
"""

import cv2
import numpy as np
import torch

class Stage5OCRDecoder:
    def __init__(self, languages=['ru', 'en'], use_gpu=True):
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.languages = languages
        self.rapid_ocr = None
        self.easy_ru = None
        self.easy_en = None
        self._init_engines()
        
        # OpenCV QR & Barcode detectors
        self.qr_detector = cv2.QRCodeDetector()
        try:
            self.barcode_detector = cv2.barcode.BarcodeDetector()
        except Exception:
            self.barcode_detector = None

    def _init_engines(self):
        # 1. Initialize RapidOCR (PP-OCRv4 ONNX)
        try:
            from rapidocr_onnxruntime import RapidOCR
            self.rapid_ocr = RapidOCR()
            print("[Stage5] RapidOCR (PP-OCRv4) ready.")
        except Exception as e:
            print(f"[Stage5] RapidOCR init error: {e}")
            self.rapid_ocr = None

        # 2. Initialize EasyOCR
        try:
            import easyocr
            self.easy_ru = easyocr.Reader(['ru'], gpu=self.use_gpu)
            self.easy_en = easyocr.Reader(['en'], gpu=self.use_gpu)
            print("[Stage5] EasyOCR (ru & en targeted readers) ready.")
        except Exception as e:
            print(f"[Stage5] EasyOCR init error: {e}")
            self.easy_ru = None
            self.easy_en = None

    def extract_text(self, img_bgr: np.ndarray) -> list[dict]:
        """
        Extracts structured text blocks with coordinates, confidence scores, and content.
        Uses RapidOCR for multilingual base and EasyOCR for targeted Cyrillic enhancement.
        """
        if img_bgr is None or img_bgr.size == 0:
            return []

        h, w = img_bgr.shape[:2]
        
        # 1. Super-Resolution Scaling & CLAHE Contrast Boosting
        scale = 1.5 if max(h, w) < 1200 else 1.0
        if scale > 1.0:
            img_proc = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LANCZOS4)
        else:
            img_proc = img_bgr.copy()

        # CLAHE Contrast Boost on Luminance
        lab = cv2.cvtColor(img_proc, cv2.COLOR_BGR2LAB)
        l_chan, a_chan, b_chan = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enh = clahe.apply(l_chan)
        img_enh = cv2.cvtColor(cv2.merge([l_enh, a_chan, b_chan]), cv2.COLOR_LAB2BGR)

        text_blocks = []

        # 2. Primary High-Precision Multilingual Extraction via RapidOCR
        if self.rapid_ocr is not None:
            try:
                rapid_results, _ = self.rapid_ocr(img_enh)
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
            except Exception as e:
                print(f"[Stage5] RapidOCR reading error: {e}")

        # 3. Targeted Cyrillic Verification & Augmentation via EasyOCR (ru)
        if self.easy_ru is not None:
            try:
                cyrillic_chars = set("абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")
                easy_ru_results = self.easy_ru.readtext(cv2.cvtColor(img_enh, cv2.COLOR_BGR2RGB))
                for bbox, text, conf in easy_ru_results:
                    clean_text = text.strip()
                    has_cyr = sum(c in cyrillic_chars for c in clean_text) >= 2
                    if has_cyr and float(conf) > 0.60:
                        pts = np.array(bbox, dtype=np.float64) / scale
                        x_min, y_min = np.min(pts, axis=0)
                        x_max, y_max = np.max(pts, axis=0)
                        
                        # Match with existing text blocks
                        matched = False
                        for b in text_blocks:
                            bx, by, bw, bh = b["rect"]["x"], b["rect"]["y"], b["rect"]["w"], b["rect"]["h"]
                            ix1, iy1 = max(x_min, bx), max(y_min, by)
                            ix2, iy2 = min(x_max, bx + bw), min(y_max, by + bh)
                            if ix2 > ix1 and iy2 > iy1:
                                inter_area = (ix2 - ix1) * (iy2 - iy1)
                                union_area = (x_max - x_min) * (y_max - y_min) + bw * bh - inter_area
                                if inter_area / max(union_area, 1.0) > 0.3:
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
            except Exception as e:
                print(f"[Stage5] EasyOCR ru verification error: {e}")

        # Sort top to bottom, then left to right
        text_blocks.sort(key=lambda b: (b["rect"]["y"], b["rect"]["x"]))
        return text_blocks

    def decode_graphical_codes(self, img_bgr: np.ndarray) -> list[dict]:
        """
        Decodes Barcodes and QR Codes from the rectified flat image.
        """
        codes = []
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # 1. OpenCV QRCodeDetector
        try:
            val, points, _ = self.qr_detector.detectAndDecode(gray)
            if val and points is not None:
                pts = points[0].astype(np.int32).tolist()
                codes.append({
                    "type": "QR_CODE",
                    "data": val,
                    "polygon": pts
                })
        except Exception as e:
            print(f"[Stage5] QR decode notice: {e}")

        # 2. OpenCV Barcode detector
        if self.barcode_detector is not None:
            try:
                ret = self.barcode_detector.detectAndDecode(gray)
                if ret and len(ret) >= 2 and ret[0]:
                    decoded_info = ret[1]
                    for info in decoded_info:
                        if info:
                            codes.append({
                                "type": "BARCODE",
                                "data": str(info),
                                "polygon": []
                            })
            except Exception as e:
                print(f"[Stage5] Barcode decode notice: {e}")

        # 3. Optional pyzbar fallback
        try:
            from pyzbar.pyzbar import decode as zbar_decode
            z_results = zbar_decode(gray)
            for z in z_results:
                data_str = z.data.decode('utf-8', errors='ignore')
                polygon = [[p.x, p.y] for p in z.polygon]
                if not any(c["data"] == data_str for c in codes):
                    codes.append({
                        "type": z.type,
                        "data": data_str,
                        "polygon": polygon
                    })
        except Exception:
            pass

        return codes

    def draw_ocr_annotations(self, img_bgr: np.ndarray, text_blocks: list[dict], codes: list[dict]) -> np.ndarray:
        """
        Draws glowing Apple-style bounding boxes and labels for recognized text and barcodes.
        """
        annotated = img_bgr.copy()
        
        # Draw text blocks
        for tb in text_blocks:
            pts = np.array(tb["bbox"], dtype=np.int32)
            cv2.polylines(annotated, [pts], isClosed=True, color=(0, 220, 100), thickness=2, lineType=cv2.LINE_AA)
            
            # Subtle semi-transparent fill
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [pts], color=(0, 220, 100))
            cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)

        # Draw graphical codes
        for c in codes:
            pts = np.array(c["polygon"], dtype=np.int32)
            cv2.polylines(annotated, [pts], isClosed=True, color=(0, 240, 255), thickness=3, lineType=cv2.LINE_AA)

        return annotated

    def process(self, dewarped_bgr: np.ndarray) -> dict:
        """Full Stage 5 execution"""
        text_blocks = self.extract_text(dewarped_bgr)
        codes = self.decode_graphical_codes(dewarped_bgr)
        annotated_bgr = self.draw_ocr_annotations(dewarped_bgr, text_blocks, codes)

        full_text = " ".join([b["text"] for b in text_blocks])

        return {
            "text_blocks": text_blocks,
            "codes": codes,
            "full_text": full_text,
            "annotated_bgr": annotated_bgr,
            "num_words": len(text_blocks)
        }
