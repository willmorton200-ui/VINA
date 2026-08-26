import cv2
import numpy as np
from ultralytics import YOLO

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

yolo = YOLO(r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt")
results = yolo.predict(img_bgr, conf=0.15, device="cuda:0")

vis = img_bgr.copy()
for r in results:
    boxes = r.boxes.xyxy.cpu().numpy()
    confs = r.boxes.conf.cpu().numpy()
    for idx, (b, c) in enumerate(zip(boxes, confs)):
        bx1, by1, bx2, by2 = b.astype(int)
        bw_b, bh_b = bx2 - bx1, by2 - by1
        area = bw_b * bh_b
        print(f"[{idx:02d}] conf={c:.2f} | box=[{bx1:3d}, {by1:3d}, {bx2:3d}, {by2:3d}] | w={bw_b:3d}, h={bh_b:3d}, area={area:6d}")
        cv2.rectangle(vis, (bx1, by1), (bx2, by2), (0, 255, 0), 2)
        cv2.putText(vis, f"{idx}: {c:.2f}", (bx1, by1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

cv2.imwrite("scratch_debug/all_liria_yolo_boxes.png", vis)
print("Saved scratch_debug/all_liria_yolo_boxes.png")
