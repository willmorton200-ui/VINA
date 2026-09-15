import cv2
import time
import torch
import numpy as np

img_path = 'test_dataset/butilki/photo_2026-08-11_21-10-14.jpg'
img_bgr = cv2.imread(img_path)

print(f"Profiling High-Speed Mode on RTX 3090 (cuda:0)...")

# 1. High-Speed Segmentation: Trained YOLOv8x-seg directly (no heavy CPU Retinex loop, no slow SAM ViT-H on 4K)
from ultralytics import YOLO
yolo = YOLO(r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt")

# Warmup
_ = yolo.predict(img_bgr, verbose=False, device="cuda:0", conf=0.25)

t0 = time.perf_counter()
yolo_res = yolo.predict(img_bgr, verbose=False, device="cuda:0", conf=0.25)
# Extract mask directly from YOLO
if yolo_res[0].masks is not None:
    mask_data = yolo_res[0].masks.data[0].cpu().numpy()
    mask_full = (cv2.resize(mask_data, (img_bgr.shape[1], img_bgr.shape[0])) > 0.5).astype(np.uint8) * 255
else:
    mask_full = np.zeros(img_bgr.shape[:2], dtype=np.uint8)
t_stage1 = (time.perf_counter() - t0) * 1000.0

# 2. High-Speed Vectorization & Coon's Patch Dewarping
from pipeline.vectorizer import MaskVectorizer
from pipeline.multi_label_engine import MultiLabelBottleEngine
vec_engine = MaskVectorizer()
engine = MultiLabelBottleEngine(use_gpu=True)

# Crop
coords = cv2.findNonZero(mask_full)
if coords is not None:
    x, y, w, h = cv2.boundingRect(coords)
    crop_bgr = img_bgr[y:y+h, x:x+w]
    crop_mask = mask_full[y:y+h, x:x+w]
else:
    crop_bgr = img_bgr
    crop_mask = mask_full

t0 = time.perf_counter()
vec = vec_engine.vectorize(crop_mask)
dewarped = engine._dewarp_coons_patch(crop_bgr, vec)
t_geom = (time.perf_counter() - t0) * 1000.0

# 3. High-Speed OCR (RapidOCR PP-OCRv4 with ONNX Runtime + Domain Lexicon Corrector)
from rapidocr_onnxruntime import RapidOCR
from pipeline.wine_lexicon_corrector import WineVocabularyCorrector
rapid = RapidOCR()
corrector = WineVocabularyCorrector()

# Warmup
_ = rapid(dewarped)

t0 = time.perf_counter()
rapid_res, _ = rapid(dewarped)
text_lines = [r[1] for r in rapid_res] if rapid_res else []
raw_text = " ".join(text_lines)
clean_text, fixes = corrector.correct_text(raw_text)
t_ocr = (time.perf_counter() - t0) * 1000.0

total_fast_ms = t_stage1 + t_geom + t_ocr

print(f"\n========================================================")
print(f"HIGH-SPEED PIPELINE RESULTS ON RTX 3090:")
print(f"========================================================")
print(f"1. Сегментация (YOLOv8x-seg на GPU):           {t_stage1:6.1f} ms")
print(f"2. Геометрия & 3D Coon's Patch Развертка:       {t_geom:6.1f} ms")
print(f"3. OCR + Винный словарь автокоррекции:         {t_ocr:6.1f} ms")
print(f"--------------------------------------------------------")
print(f"ИТОГОВОЕ ВРЕМЯ ОБРАБОТКИ:                     {total_fast_ms:6.1f} ms ({total_fast_ms/1000.0:.2f} сек)")
print(f"УСКОРЕНИЕ (SPEEDUP):                           {7130.0 / total_fast_ms:.1f}x РАЗ БЫСТРЕЕ!")
print(f"Распознанный текст: {clean_text}")
