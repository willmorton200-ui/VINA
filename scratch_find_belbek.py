import cv2
import glob
from pipeline.stage5_ocr import Stage5OCRDecoder

ocr = Stage5OCRDecoder()
for f in sorted(glob.glob("test_dataset/butilki/*.jpg")):
    img = cv2.imread(f)
    h, w = img.shape[:2]
    # Fast OCR on center crop
    crop = img[int(h*0.3):int(h*0.8), int(w*0.2):int(w*0.8)]
    res = ocr.process(crop)
    text = " ".join([t["text"] for t in res.get("text_blocks", [])])
    if "БЕЛЬБЕК" in text.upper() or "МУСКАТ" in text.upper() or "BELBEK" in text.upper() or "СУХОЕ" in text.upper():
        print(f"FOUND BELBEK in {f}: {text}")
        break
