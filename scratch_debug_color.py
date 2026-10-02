import cv2
import json
import os
from pipeline.stage5_ocr import OCRExtractor
from pipeline.catalog import WineCatalog

cat = WineCatalog()
ocr = OCRExtractor()
img_path = r"D:\VINA\TZ\Датасет\Датасет\eval\queries\2059dd8a.jpg"
if not os.path.exists(img_path):
    print("Image not found")
else:
    img = cv2.imread(img_path)
    text = ocr.extract_text(img)
    print("OCR Text:", text)
    
    from pipeline.vina_studio_matcher import extract_ocr_words, check_color_contradiction
    
    words = extract_ocr_words(text)
    print("OCR Words extracted:", words)
    
    slugs = [
        "alma-valley-alma-graviti-pino-nuar-merlo-kaberne-sovinon-krasnoe-suhoe-14",
        "alma-valley-graviti-pino-blan-beloe-suhoe-135"
    ]
    for s in slugs:
        w_info = cat.get_wine(s)
        contradiction = check_color_contradiction(words, s, w_info)
        print(f"Slug: {s}, Contradiction: {contradiction}")

