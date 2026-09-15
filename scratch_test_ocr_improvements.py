import cv2
import numpy as np
import easyocr

# Load the dewarped image of Michel Schneider
img_path = r"D:\VINA\outputs\test_michel_extreme\photo_2026-08-10_12-34-30 (2)\flattened_image.png"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

print("=== 1. TEST BASELINE EASYOCR (ru + en) ===")
reader_ru_en = easyocr.Reader(['ru', 'en'], gpu=True)
res_ru_en = reader_ru_en.readtext(img_bgr, detail=0)
print("EasyOCR (ru+en):", " ".join(res_ru_en))

print("\n=== 2. TEST EASYOCR (English/Latin only, without Cyrillic confusion) ===")
reader_en = easyocr.Reader(['en'], gpu=True)
res_en = reader_en.readtext(img_bgr, detail=0)
print("EasyOCR (en only):", " ".join(res_en))

print("\n=== 3. TEST WITH 2x BICUBIC UPSCALE & SHARPENING ===")
# 2x upscale + unsharp mask
img_2x = cv2.resize(img_bgr, (w * 2, h * 2), interpolation=cv2.INTER_LANCZOS4)
gaussian = cv2.GaussianBlur(img_2x, (0, 0), 2.0)
img_sharp = cv2.addWeighted(img_2x, 1.5, gaussian, -0.5, 0)

res_sharp = reader_en.readtext(img_sharp, detail=0)
print("EasyOCR (en + 2x Sharp):", " ".join(res_sharp))

print("\n=== 4. TEST PADDLEOCR IF INSTALLED ===")
try:
    import importlib
    paddleocr_module = importlib.import_module("paddleocr")
    PaddleOCR = getattr(paddleocr_module, "PaddleOCR")
    ocr_paddle = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=True)
    res_paddle = ocr_paddle.ocr(img_bgr)
    paddle_texts = [line[1][0] for line in res_paddle[0]] if res_paddle and res_paddle[0] else []
    print("PaddleOCR (en):", " ".join(paddle_texts))
except Exception as e:
    print(f"PaddleOCR test: {e}")

print("\n=== 5. TEST FLORENCE-2 / VISION MODEL IF AVAILABLE ===")
try:
    from transformers import AutoProcessor, AutoModelForCausalLM
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Loading Florence-2...")
    model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True).eval().to(device)
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
    
    from PIL import Image
    pil_img = Image.open(img_path).convert("RGB")
    inputs = processor(text="<OCR>", images=pil_img, return_tensors="pt").to(device)
    generated_ids = model.generate(input_ids=inputs["input_ids"], pixel_values=inputs["pixel_values"], max_new_tokens=1024)
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed_answer = processor.post_process_generation(generated_text, task="<OCR>", image_size=pil_img.size)
    print("Florence-2 OCR:", parsed_answer.get("<OCR>", ""))
except Exception as e:
    print(f"Florence-2 test: {e}")
