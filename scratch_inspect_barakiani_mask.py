import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')
h, w = img.shape[:2]

# Run YOLO detection directly
results = p1.yolo_model(img, conf=0.25, device=p1.device)
boxes = []
for r in results:
    for box in r.boxes:
        xyxy = box.xyxy[0].cpu().numpy()
        conf = float(box.conf[0].cpu().numpy())
        cls_id = int(box.cls[0].cpu().numpy())
        cls_name = p1.yolo_model.names[cls_id]
        boxes.append((xyxy, conf, cls_id, cls_name))

print(f"YOLO detected {len(boxes)} objects on Barakiani image:")
for i, (b, c, cid, cname) in enumerate(boxes):
    print(f"  Box {i+1}: {cname} (conf={c:.2f}) -> [{int(b[0])}, {int(b[1])}, {int(b[2])}, {int(b[3])}]")

# Visualize YOLO boxes
vis_yolo = img.copy()
for b, c, cid, cname in boxes:
    cv2.rectangle(vis_yolo, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 255, 0), 3)
    cv2.putText(vis_yolo, f"{cname} {c:.2f}", (int(b[0]), int(b[1])-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

# Run full segment_bottle_and_label
crop_bgr, mask_crop, bbox_info = p1.segment_bottle_and_label(img)

# Overlay mask on crop
vis_mask_overlay = crop_bgr.copy()
vis_mask_overlay[mask_crop > 127] = cv2.addWeighted(crop_bgr[mask_crop > 127], 0.5, np.full_like(crop_bgr[mask_crop > 127], (0, 255, 0)), 0.5, 0)

cv2.imwrite(os.path.join(artifacts_dir, "barakiani_yolo_detections.png"), vis_yolo)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_current_mask_overlay.png"), vis_mask_overlay)
cv2.imwrite(os.path.join(artifacts_dir, "barakiani_current_mask_binary.png"), mask_crop)

print("Saved inspection images to artifacts.")
