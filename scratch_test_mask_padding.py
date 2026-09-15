import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer

img_path = "d:/VINA/test_dataset/butilki/castillo_liria_pair.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]
print(f"Loaded {img_path}: {w}x{h}")

stage1 = Stage1Preprocessor(use_gpu=True)
vectorizer = MaskVectorizer()

# Run YOLO & segment
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.20)
print(f"Number of masks: {len(yolo_res[0].masks.data) if yolo_res[0].masks is not None else 0}")

# Get candidate masks
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()

for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs)):
    cls_name = stage1.yolo_model.names.get(int(cls_id), str(cls_id))
    print(f"Det {idx}: {cls_name} ({cls_id}), conf={conf:.2f}, box={[int(v) for v in box]}")

# Pick dominant label (Castillo de Liria)
# Let's inspect the largest mask
cropped_bgr, cropped_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)
print(f"Initial cropped_bgr shape: {cropped_bgr.shape}")
print(f"Initial cropped_mask shape: {cropped_mask.shape}")

# Find non-zero bounds
coords = cv2.findNonZero((cropped_mask > 127).astype(np.uint8))
if coords is not None:
    mx, my, mw, mh = cv2.boundingRect(coords)
    print(f"Mask actual bounds inside crop: x={mx}, y={my}, w={mw}, h={mh} (Crop is {cropped_bgr.shape[1]}x{cropped_bgr.shape[0]})")
    print(f"Left margin: {mx}px, Right margin: {cropped_bgr.shape[1] - (mx + mw)}px, Top: {my}px, Bottom: {cropped_bgr.shape[0] - (my + mh)}px")

os.makedirs("scratch_debug", exist_ok=True)
cv2.imwrite("scratch_debug/castillo_pair_loose_crop.png", cropped_bgr)
cv2.imwrite("scratch_debug/castillo_pair_loose_mask.png", cropped_mask)
