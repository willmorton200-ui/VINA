import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor

stage1 = Stage1Preprocessor(use_gpu=True)
img_bgr = cv2.imread("d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-09.jpg")
h, w = img_bgr.shape[:2]

# Let's inspect Stage 1 step by step
crop_bgr, crop_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)
print(f"Final Crop shape: {crop_bgr.shape}")
print(f"bbox_info: crop_x={bbox_info['crop_x']}, crop_y={bbox_info['crop_y']}, crop_w={bbox_info['crop_w']}, crop_h={bbox_info['crop_h']}")

# Let's check which winner was chosen
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.10)
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()

# Check hierarchical suppression
parsed_candidates = []
for idx, (b, conf) in enumerate(zip(boxes, confs)):
    bx1, by1, bx2, by2 = [int(v) for v in b]
    bw_box, bh_box = max(1, bx2 - bx1), max(1, by2 - by1)
    ar = bw_box / float(bh_box)
    area = bw_box * bh_box
    if ar < 0.15 or ar > 3.5 or bw_box > 0.90 * w or bh_box > 0.92 * h or area < 0.005 * (w * h):
        continue
    touches_border = (bx1 <= 10 or by1 <= 10 or bx2 >= w - 10 or by2 >= h - 10)
    parsed_candidates.append({
        "idx": idx, "box": [bx1, by1, bx2, by2], "bw": bw_box, "bh": bh_box, "ar": ar, "area": area,
        "conf": float(conf), "touches_border": touches_border
    })

suppressed_indices = set()
for i, c_a in enumerate(parsed_candidates):
    ax1, ay1, ax2, ay2 = c_a["box"]
    for j, c_b in enumerate(parsed_candidates):
        if i == j:
            continue
        bx1, by1, bx2, by2 = c_b["box"]
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        if ix2 > ix1 and iy2 > iy1:
            inter_area = (ix2 - ix1) * (iy2 - iy1)
            if inter_area >= 0.70 * c_b["area"] and c_a["area"] >= 1.5 * c_b["area"]:
                if c_b["conf"] >= c_a["conf"] - 0.15:
                    suppressed_indices.add(i)
                    print(f"Candidate {i} {c_a['box']} (area={c_a['area']}) SUPPRESSED by Candidate {j} {c_b['box']} (area={c_b['area']})")

print(f"Suppressed indices: {suppressed_indices}")
