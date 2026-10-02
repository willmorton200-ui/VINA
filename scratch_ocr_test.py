import cv2
import json
from pipeline import CylindricalDewarpEngine

img_path = r"D:\VINA\owner_eval\1\queries\e3f116c0.jpeg"
print(f"Processing: {img_path}")

img = cv2.imread(img_path)
if img is None:
    print("Could not load image")
    exit(1)

engine = CylindricalDewarpEngine(use_gpu=True)
res = engine.process_image(img)

if res.get("success"):
    print("\n--- OCR Text Blocks ---")
    for b in res.get("artifacts", {}).get("text_blocks", []):
        print(f"Text: '{b.get('text')}' | Conf: {b.get('confidence')} | Box: {b.get('rect')}")
    
    print(f"\nFull text: {res.get('full_text')}")
    
    annotated = res.get("annotated_bgr")
    if annotated is not None:
        cv2.imwrite(r"D:\VINA\test_ocr_result.jpg", annotated)
        print("Saved annotated image to D:/VINA/test_ocr_result.jpg")
else:
    print(f"Pipeline failed: {res.get('error')}")
