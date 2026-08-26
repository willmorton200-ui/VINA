import time
import cv2
import numpy as np
import torch
from pipeline.stage1_preprocessing import Stage1Preprocessor

img = cv2.imread("test_dataset/butilki/photo_2026-08-11_21-10-10.jpg")
p1 = Stage1Preprocessor()

t0 = time.perf_counter()
# 1. YOLO
res_yolo = p1.yolo_model.predict(img, verbose=False, device=p1.device, conf=0.25)
t_yolo = time.perf_counter()

# 2. SAM
box = [120, 50, 730, 850]
sam_mask, sam_score = p1.sam_refiner.refine_mask(img, box)
t_sam = time.perf_counter()

# 3. Retinex & Enhancements
crop, mask, info = p1.segment_bottle_and_label(img)
t_crop = time.perf_counter()

res_s1 = p1.process(img)
t_total = time.perf_counter()

print("STAGE 1 DETAILED BREAKDOWN:")
print(f"  YOLO inference:     {(t_yolo - t0)*1000:.1f} ms")
print(f"  SAM ViT-H Refine:   {(t_sam - t_yolo)*1000:.1f} ms")
print(f"  Stage 1 Total:      {(t_total - t_crop)*1000:.1f} ms")
