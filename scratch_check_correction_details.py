import cv2
from pipeline.stage5_ocr import Stage5OCRDecoder
from pipeline.wine_lexicon_corrector import WineVocabularyCorrector

ocr = Stage5OCRDecoder(use_gpu=True)
corrector = WineVocabularyCorrector()

# Let's test with various inputs
test_strings = [
    "TEMIIPAHIIbO",
    "TEMIIPAHMJIbO",
    "РАСНОЕ",
    "РАСНОЕ СУХОЕ ВИНО",
    "РАСНОЕ СУХОЕ ВИНО КРЫМ",
    "TEMIIPAHIIbO 2024 РАСНОЕ СУХОЕ ВИНО КРЫМ",
    "TEMIIPAHIIbO 2024 РАСНОЕ СУХОЕ ВИНО РОССИЯ",
    "ТЕМПРАНИЛЬО 2024 КРАСНОЕ СУХОЕ ВИНО КРЫМ РОССИЯ Alma Valley"
]

print("Testing direct corrector:")
for s in test_strings:
    res, fixes = corrector.correct_text(s)
    print(f"  IN:  {s}")
    print(f"  OUT: {res}")
    print(f"  FIX: {fixes}\n")
