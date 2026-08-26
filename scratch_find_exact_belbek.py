import cv2
import glob
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.stage5_ocr import Stage5OCRDecoder

p1 = Stage1Preprocessor()
ocr = Stage5OCRDecoder()

for f in sorted(glob.glob("test_dataset/butilki/photo_2026-08-11_*.jpg")):
    img = cv2.imread(f)
    crop, mask, info = p1.segment_bottle_and_label(img)
    res = ocr.process(crop)
    text = " | ".join([t["text"] for t in res.get("text_blocks", [])])
    print(f"--- {f} ---")
    print(f"  OCR: {text}")
    if "МУСКАТ" in text.upper() or "БЕЛЬБЕК" in text.upper() or "БЕЛ" in text.upper():
        print(f"===> MATCHED BELBEK in {f}")
