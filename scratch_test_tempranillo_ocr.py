import cv2
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer
from pipeline.stage5_ocr import Stage5OCRDecoder
from pipeline.multi_label_engine import MultiLabelBottleEngine

img_path = 'test_dataset/butilki/photo_2026-08-11_21-10-14.jpg'
img_bgr = cv2.imread(img_path)

p1 = Stage1Preprocessor(use_gpu=True)
crop_bgr, mask_crop, _ = p1.segment_bottle_and_label(img_bgr)

vec = MaskVectorizer().vectorize(mask_crop)
engine = MultiLabelBottleEngine(use_gpu=True)
dewarped = engine._dewarp_coons_patch(crop_bgr, vec)

ocr = Stage5OCRDecoder(use_gpu=True)
res = ocr.process(dewarped)

print('\n======================================================')
print('=== OCR RESULT WITH DOMAIN WINE LEXICON AUTO-CORRECTION ===')
print('======================================================')
print('Full Text:', res['full_text'])
print('\nApplied Lexicon Corrections:')
for fix in res['lexicon_corrections']:
    print('  *', fix)
print('\nTokens:')
for tb in res['text_blocks']:
    conf_val = tb['confidence']
    print(f"  - {tb['text']} (conf: {conf_val:.2f})")
