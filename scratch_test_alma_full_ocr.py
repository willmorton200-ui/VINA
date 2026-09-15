import cv2
import numpy as np
from pipeline.dewarp_engine import CylindricalDewarpEngine

engine = CylindricalDewarpEngine()
img_bgr = cv2.imread("d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-16.jpg")
res = engine.process_image(img_bgr)

print("Status:", res.get("decision_status"))
print("Dewarped Full text:\n", res["comparison"]["dewarped"]["full_text"])
print("Raw Full text:\n", res["comparison"]["raw"]["full_text"])
print("Final Full text:\n", res.get("full_text"))
print("Tokens:\n", [t["text"] for t in res.get("text_blocks", [])])
print("Corrections:\n", res.get("lexicon_corrections"))
