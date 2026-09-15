import cv2
import time
import torch
import numpy as np

img_path = 'test_dataset/butilki/photo_2026-08-11_21-10-14.jpg'
img_bgr = cv2.imread(img_path)

print(f"CUDA Available: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0)}")

# 1. Profile YOLO detection & segmentation
from ultralytics import YOLO
yolo = YOLO(r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt")

t0 = time.perf_counter()
yolo_res = yolo.predict(img_bgr, verbose=False, device="cuda:0", conf=0.25)
t_yolo = (time.perf_counter() - t0) * 1000.0
print(f"1. YOLOv8x-seg on RTX 3090: {t_yolo:.1f} ms")

# 2. Profile SAM ViT-H
from pipeline.sam_refiner import SAMRefiner
sam = SAMRefiner(device="cuda:0")
if sam.is_ready():
    box = [int(v) for v in yolo_res[0].boxes.xyxy[0].cpu().numpy()]
    t0 = time.perf_counter()
    mask, _ = sam.refine_mask(img_bgr, box)
    t_sam = (time.perf_counter() - t0) * 1000.0
    print(f"2. SAM ViT-H (Huge 2.5GB model) on full image: {t_sam:.1f} ms")

# 3. Profile Vectorizer & Coon's Patch Dewarping
from pipeline.vectorizer import MaskVectorizer
from pipeline.multi_label_engine import MultiLabelBottleEngine
vec_engine = MaskVectorizer()
engine = MultiLabelBottleEngine(use_gpu=True)

h, w = img_bgr.shape[:2]
t0 = time.perf_counter()
vec = vec_engine.vectorize(mask)
dewarped = engine._dewarp_coons_patch(img_bgr, vec)
t_geom = (time.perf_counter() - t0) * 1000.0
print(f"3. Vectorization + Coon's Patch Grid + Lanczos-4 Dewarping: {t_geom:.1f} ms")

# 4. Profile RapidOCR vs EasyOCR
from rapidocr_onnxruntime import RapidOCR
rapid = RapidOCR()

t0 = time.perf_counter()
rapid_res, _ = rapid(dewarped)
t_rapid = (time.perf_counter() - t0) * 1000.0
print(f"4. RapidOCR (PP-OCRv4 ONNX): {t_rapid:.1f} ms")

import easyocr
easy_ru = easyocr.Reader(['ru'], gpu=True)
t0 = time.perf_counter()
easy_res = easy_ru.readtext(cv2.cvtColor(dewarped, cv2.COLOR_BGR2RGB))
t_easy = (time.perf_counter() - t0) * 1000.0
print(f"5. EasyOCR (PyTorch CRAFT + Rec): {t_easy:.1f} ms")

print("\n------------------------------------------------------")
print(f"TOTAL Current Time: {t_yolo + t_sam + t_geom + t_rapid + t_easy:.1f} ms (~{(t_yolo + t_sam + t_geom + t_rapid + t_easy)/1000.0:.2f} sec)")
print(f"POTENTIAL Optimized Time (YOLO + Fast SAM/Direct + RapidOCR ONNX): {t_yolo + 15 + t_geom + t_rapid:.1f} ms (~{(t_yolo + 15 + t_geom + t_rapid)/1000.0:.2f} sec)")
