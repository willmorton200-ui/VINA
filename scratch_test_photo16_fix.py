import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.10)
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()

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
    # Whole bottle body container filter
    is_container = (c_a["bh"] >= 0.75 * h or c_a["area"] >= 0.50 * (w * h))
    if not is_container:
        continue
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

valid_candidates = [c for i, c in enumerate(parsed_candidates) if i not in suppressed_indices]

max_conf = max(c["conf"] for c in valid_candidates)
for c in valid_candidates:
    bx1, by1, bx2, by2 = c["box"]
    cx_box = (bx1 + bx2) / 2.0
    dist_ratio = abs(cx_box - w / 2.0) / (w / 2.0)
    centrality_weight = max(0.1, 1.0 - 0.6 * dist_ratio)
    border_penalty = 0.15 if c["touches_border"] else 1.0
    conf_weight = (c["conf"] / max(max_conf, 1e-4)) ** 4
    if 0.40 <= c["ar"] <= 2.2:
        ar_weight = 1.0
    elif 0.25 <= c["ar"] < 0.40:
        ar_weight = 0.7
    else:
        ar_weight = 0.4
    c["score"] = (c["area"] ** 0.5) * conf_weight * centrality_weight * border_penalty * ar_weight

valid_candidates.sort(key=lambda item: item["score"], reverse=True)
winner = valid_candidates[0]
print("Winner Box for Photo 16:", winner["box"], "Conf:", winner["conf"], "Area:", winner["area"], "Score:", winner["score"])
