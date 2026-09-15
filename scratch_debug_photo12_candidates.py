import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor

img_path = "d:/VINA/test_dataset/butilki/photo_2026-08-11_21-10-12.jpg"
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.10)

boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
confs = yolo_res[0].boxes.conf.cpu().numpy()
classes = yolo_res[0].boxes.cls.cpu().numpy()
masks_data = yolo_res[0].masks.data.cpu().numpy() if yolo_res[0].masks is not None else None

print(f"Total detections: {len(boxes)}")
scored_candidates = []
for idx, (b, c, cls_id) in enumerate(zip(boxes, confs, classes)):
    bx1, by1, bx2, by2 = [int(v) for v in b]
    bw_box, bh_box = max(1, bx2 - bx1), max(1, by2 - by1)
    ar = bw_box / float(bh_box)
    
    passes_filter = (0.20 <= ar <= 2.20 and bw_box <= 0.75 * w and bh_box <= 0.90 * h)
    
    if masks_data is not None and idx < len(masks_data):
        m_raw = masks_data[idx]
        m_full = (cv2.resize(m_raw, (w, h)) > 0.5).astype(np.uint8) * 255
        m_full = stage1._keep_largest_component(m_full)
        
        top_contact = np.count_nonzero(m_full[:2, :])
        bot_contact = np.count_nonzero(m_full[h-2:, :])
        left_contact = np.count_nonzero(m_full[:, :2])
        right_contact = np.count_nonzero(m_full[:, w-2:])
        total_contact = top_contact + bot_contact + left_contact + right_contact
        
        pixel_area = np.count_nonzero(m_full)
        penalty = total_contact * 1000.0 if total_contact > 10 else 0.0
        score = pixel_area - penalty
        
        print(f"\nCandidate {idx}: box=[{bx1}, {by1}, {bx2}, {by2}] (w={bw_box}, h={bh_box}, ar={ar:.2f}, conf={c:.2f})")
        print(f"  passes_filter: {passes_filter}")
        print(f"  pixel_area: {pixel_area} ({pixel_area/(w*h):.3f} of image)")
        print(f"  contact: top={top_contact}, bot={bot_contact}, left={left_contact}, right={right_contact}, total={total_contact}")
        print(f"  penalty: {penalty}, score: {score}")
        
        if passes_filter and pixel_area >= 0.015 * (w * h):
            scored_candidates.append({
                "idx": idx,
                "box": [bx1, by1, bx2, by2],
                "area": pixel_area,
                "score": score
            })

scored_candidates.sort(key=lambda item: item["score"], reverse=True)
print("\n--- Sorted Ranked Candidates ---")
for r, cand in enumerate(scored_candidates):
    print(f"Rank {r}: idx={cand['idx']}, box={cand['box']}, area={cand['area']}, score={cand['score']}")
