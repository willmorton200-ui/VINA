import cv2
import numpy as np
import os
import torch

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-30 (3).jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

from ultralytics import YOLO
yolo_path = r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt"
model = YOLO(yolo_path)

results = model.predict(img_bgr, conf=0.15, device="cuda:0" if torch.cuda.is_available() else "cpu")

vis_yolo = img_bgr.copy()
for r in results:
    boxes = r.boxes.xyxy.cpu().numpy()
    confs = r.boxes.conf.cpu().numpy()
    classes = r.boxes.cls.cpu().numpy()
    names = r.names
    print(f"Detected {len(boxes)} objects:")
    for b, c, cl in zip(boxes, confs, classes):
        cls_name = names.get(int(cl), str(cl))
        print(f"  Class: {cls_name} ({cl}), Conf: {c:.3f}, Box: {b.astype(int)}")
        cv2.rectangle(vis_yolo, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 255, 0), 2)
        cv2.putText(vis_yolo, f"{cls_name} {c:.2f}", (int(b[0]), int(b[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

os.makedirs("scratch_debug", exist_ok=True)
cv2.imwrite("scratch_debug/terra_yolo_detections.png", vis_yolo)
print("Saved scratch_debug/terra_yolo_detections.png")
