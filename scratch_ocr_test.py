import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

img_path = r"D:\VINA\test_dataset\butilki\monastyrskaya_izba.jpg"
img = cv2.imread(img_path)

if img is None:
    print("Image not found!")
    exit()

ocr = RapidOCR(det_unclip_ratio=1.9, det_db_box_thresh=0.38)
results, _ = ocr(img)

vis = img.copy()
if results:
    for bbox, text, conf in results:
        pts = np.array(bbox, np.int32)
        cv2.polylines(vis, [pts], True, (0, 255, 0), 2)
        # Draw corners
        for p in pts:
            cv2.circle(vis, tuple(p), 3, (0, 0, 255), -1)
        
        print(f"Text: {text}, Points: {pts.tolist()}")

cv2.imwrite("ocr_test_boxes.jpg", vis)
print("Saved ocr_test_boxes.jpg")
