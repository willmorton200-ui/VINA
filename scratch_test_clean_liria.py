import cv2
import numpy as np
import os
from pipeline.vectorizer import MaskVectorizer

# Load original mask for photo_2026-08-10_12-34-29
img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

# 1. Run YOLO to detect labels
from ultralytics import YOLO
yolo = YOLO(r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt")
results = yolo.predict(img_bgr, conf=0.25, device="cuda:0")

# 2. Pick the primary central label
r = results[0]
boxes = r.boxes.xyxy.cpu().numpy()
confs = r.boxes.conf.cpu().numpy()

# Central bottle label
best_idx = 0
best_dist = 999999
for idx, (b, c) in enumerate(zip(boxes, confs)):
    cx = (b[0] + b[2]) / 2.0
    dist = abs(cx - w / 2.0)
    if dist < best_dist:
        best_dist = dist
        best_idx = idx

target_box = boxes[best_idx].astype(int)
print(f"Target dominant label box: {target_box}")

# 3. Refine with SAM ViT-H
from pipeline.sam_refiner import SAMRefiner
sam = SAMRefiner()
mask_sam, score = sam.refine_mask(img_bgr, target_box.tolist())

# Clean to SINGLE largest component
binary = np.uint8(mask_sam > 127)
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_mask = np.zeros_like(mask_sam)
    clean_mask[labels == largest_label] = 255
    mask_sam = clean_mask

# 4. Crop to bottle label
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

# 5. Vectorize
vec = MaskVectorizer()
vm = vec.vectorize(crop_mask)

print("Clean Single-Label Vector Corners on Crop:")
print("  P_TL:", vm.P_TL)
print("  P_TR:", vm.P_TR)
print("  P_BL:", vm.P_BL)
print("  P_BR:", vm.P_BR)

# 6. Render overlay
vis = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Blue lateral lines
cv2.line(vis, (int(vm.P_TL[0]), int(vm.P_TL[1])), (int(vm.P_BL[0]), int(vm.P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis, (int(vm.P_TR[0]), int(vm.P_TR[1])), (int(vm.P_BR[0]), int(vm.P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green curves
cv2.polylines(vis, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

for pt in [vm.P_TL, vm.P_TR, vm.P_BL, vm.P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "liria_restored_single_mask.png"), vis)
print("Saved liria_restored_single_mask.png!")
