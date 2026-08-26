import cv2
import numpy as np
import os
from ultralytics import YOLO
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-31.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

yolo = YOLO(r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt")
sam = SAMRefiner()

# Run YOLO
results = yolo.predict(img_bgr, conf=0.20, device="cuda:0")
boxes = results[0].boxes.xyxy.cpu().numpy()
confs = results[0].boxes.conf.cpu().numpy()

# Select central label
best_idx = 0
best_score = -1
for idx, (b, c) in enumerate(zip(boxes, confs)):
    bx1, by1, bx2, by2 = b.astype(int)
    bw_b, bh_b = max(1, bx2 - bx1), max(1, by2 - by1)
    area = bw_b * bh_b
    ar = bw_b / float(bh_b)
    if 0.5 <= ar <= 2.2:
        dist_x = abs((bx1 + bx2) / 2.0 - w / 2.0)
        score = area * float(c) * max(0.5, 1.0 - (dist_x / (w * 0.5)))
        if score > best_score:
            best_score = score
            best_idx = idx

target_box = boxes[best_idx].astype(int)
print("Target Box on Barakiani:", target_box.tolist())

# SAM refinement
mask_sam, score = sam.refine_mask(img_bgr, target_box.tolist())

# Crop
binary = np.uint8(mask_sam > 127)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask = np.zeros_like(mask_sam)
    clean_mask[labels == largest_label] = 255
    mask_sam = clean_mask

coords = cv2.findNonZero(mask_sam)
lx, ly, lw, lh = cv2.boundingRect(coords)
pad_x = int(lw * 0.08)
pad_y = int(lh * 0.08)
x0 = max(0, lx - pad_x)
y0 = max(0, ly - pad_y)
x1 = min(w, lx + lw + pad_x)
y1 = min(h, ly + lh + pad_y)

crop_bgr = img_bgr[y0:y1, x0:x1].copy()
crop_mask = mask_sam[y0:y1, x0:x1].copy()

# Save raw crop mask to inspect spikes
os.makedirs("scratch_debug", exist_ok=True)
cv2.imwrite("scratch_debug/barakiani_raw_mask.png", crop_mask)
print("Saved scratch_debug/barakiani_raw_mask.png!")
