import cv2
import numpy as np
import os
import json
import torch
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage5_ocr import Stage5OCRDecoder
from pipeline.wine_lexicon_corrector import WineVocabularyCorrector

img_path = "d:/VINA/test_dataset/butilki/monastyrskaya_izba.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]
print(f"Loaded image {img_path}: {w}x{h}")

stage1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()
stage5 = Stage5OCRDecoder(use_gpu=True)
lexicon = WineVocabularyCorrector()

# YOLO predict
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.20)
print("Detections found:")
if yolo_res[0].masks is not None:
    boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
    classes = yolo_res[0].boxes.cls.cpu().numpy()
    confs = yolo_res[0].boxes.conf.cpu().numpy()
    for idx, (b, c, cf) in enumerate(zip(boxes, classes, confs)):
        cls_name = stage1.yolo_model.names.get(int(c), str(c))
        print(f"  Det {idx}: class={cls_name} ({c}), conf={cf:.2f}, box={[int(x) for x in b]}")

# Let's inspect the ambassador Monastyrskaya Izba label specifically
# It is around [480, 400, 850, 900] (lower white label) and [480, 300, 850, 450] (black neck/upper label)
os.makedirs("scratch_debug", exist_ok=True)
