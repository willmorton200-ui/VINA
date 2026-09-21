import cv2
import sys
import numpy as np
sys.path.append(r"d:\VINA\pipeline")
from stage5_ocr import Stage5OCRDecoder
from vectorizer import MaskVectorizer

img = cv2.imread(r"d:\VINA\test_dataset\cam\757_chteau-le-grand-vostock-le-chene-royal-reserve.jpeg")
img_crop = img[0:388, 3:297]
h, w = img_crop.shape[:2]

ocr = Stage5OCRDecoder()
ocr_data = ocr.process(img_crop)

v = MaskVectorizer()
sag = v._estimate_text_curvature(ocr_data, w, h)
print(f"Computed text sagitta: {sag}")
