import cv2
import sys
import numpy as np
sys.path.append(r"d:\VINA\pipeline")

from ultralytics import YOLO

# Load the trained model used in stage1
yolo_model = YOLO(r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt")

img_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ff223942-8c56-4dbf-86d0-d0a36dc4c092\.user_uploaded\media_1789616885445.png"
# This is a screenshot of the UI. I need the original image from the test_dataset.
# From the previous debug, the image is:
orig_img_path = r"d:\VINA\test_dataset\cam\757_chteau-le-grand-vostock-le-chene-royal-reserve.jpeg"
# Wait, the screenshot is Twiga Hills! What is the filename for Twiga Hills?
# Let's search the cam folder for twiga or sauvignon.
import glob
files = glob.glob(r"d:\VINA\test_dataset\cam\*twiga*") + glob.glob(r"d:\VINA\test_dataset\cam\*sauvignon*")
print("Found possible Twiga files:", files)

# Let's just run YOLO directly on the user's uploaded screenshot (cropping out the UI parts if needed), or just on the screenshot itself!
img = cv2.imread(img_path)
results = yolo_model(img)

out_img = img.copy()
for r in results:
    boxes = r.boxes.xyxy.cpu().numpy()
    confs = r.boxes.conf.cpu().numpy()
    for box, conf in zip(boxes, confs):
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(out_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(out_img, f"YOLO: {conf:.2f}", (x1, max(y1-10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

out_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ff223942-8c56-4dbf-86d0-d0a36dc4c092\yolo_bbox.png"
cv2.imwrite(out_path, out_img)
print(f"Saved YOLO output to {out_path}")
