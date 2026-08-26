import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

p1 = Stage1Preprocessor()
results = p1.yolo_model.predict(img_bgr, verbose=False, device=p1.device, conf=0.15)

for r in results:
    boxes = r.boxes.xyxy.cpu().numpy()
    confs = r.boxes.conf.cpu().numpy()
    classes = r.boxes.cls.cpu().numpy()
    print(f"Total detections: {len(boxes)}")
    for idx, (b, c, cls_id) in enumerate(zip(boxes, confs, classes)):
        cls_name = p1.yolo_model.names.get(int(cls_id), f"class_{cls_id}")
        bw, bh = int(b[2] - b[0]), int(b[3] - b[1])
        print(f"[{idx}] {cls_name}: conf={c*100:.1f}%, box={[int(v) for v in b]}, size={bw}x{bh}, area_ratio={bw*bh/(w*h):.3f}")
