import cv2
from pipeline.dewarp_engine import CylindricalDewarpEngine

engine = CylindricalDewarpEngine()
img_bgr = cv2.imread("d:/VINA/test_dataset/butilki/tsimlyanskoe_krepost_sarkel.jpg")
res = engine.process(img_bgr)

print("Status:", res.get("status"))
print("Dewarped base64 len:", len(res.get("dewarped_image", "")))
print("Raw OCR text:", res.get("raw_crop_ocr_text"))
print("Full text:", res.get("full_text"))
print("Tokens:", [t["text"] for t in res.get("text_blocks", [])])
print("Lexicon:", res.get("lexicon_corrections"))
