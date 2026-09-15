import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor

stage1 = Stage1Preprocessor(use_gpu=True)

for fn in ["photo_2026-08-11_21-10-09.jpg", "photo_2026-08-11_21-10-16.jpg"]:
    img_bgr = cv2.imread(f"d:/VINA/test_dataset/butilki/{fn}")
    h, w = img_bgr.shape[:2]
    
    yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.10)
    boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
    confs = yolo_res[0].boxes.conf.cpu().numpy()
    
    print(f"\n==================== {fn} ({w}x{h}) ====================")
    for idx, (b, c) in enumerate(zip(boxes, confs)):
        bx1, by1, bx2, by2 = [int(v) for v in b]
        bw, bh = bx2 - bx1, by2 - by1
        ar = bw / max(1, bh)
        print(f"Box {idx}: [{bx1}, {by1}, {bx2}, {by2}] (w={bw}, h={bh}, ar={ar:.2f}, conf={c:.2f}, area={bw*bh})")
        
    crop_bgr, crop_mask, bbox_info = stage1.segment_bottle_and_label(img_bgr)
    print("WINNER BOX:", bbox_info.get("yolo_detections", [])[0] if bbox_info.get("yolo_detections") else "None")
    print("CROP SHAPE:", crop_bgr.shape)
