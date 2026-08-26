import cv2
import numpy as np
import os
from ultralytics import YOLO
from pipeline.sam_refiner import SAMRefiner
from pipeline.vectorizer import MaskVectorizer

yolo = YOLO(r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt")
sam = SAMRefiner()
vec = MaskVectorizer()

def test_bottle_label_selection(img_path, name):
    img = cv2.imread(img_path)
    h, w = img.shape[:2]
    
    results = yolo.predict(img, conf=0.20, device="cuda:0")
    boxes = results[0].boxes.xyxy.cpu().numpy()
    confs = results[0].boxes.conf.cpu().numpy()
    
    # Filter and score candidates
    candidates = []
    for idx, (b, c) in enumerate(zip(boxes, confs)):
        bx1, by1, bx2, by2 = b.astype(int)
        bw_b, bh_b = max(1, bx2 - bx1), max(1, by2 - by1)
        area = bw_b * bh_b
        area_ratio = area / float(w * h)
        ar = bw_b / float(bh_b)
        
        # Must not be a mega-box (> 50% image) and not a tiny box (< 1.5% image)
        if 0.015 <= area_ratio <= 0.50 and bw_b <= 0.70 * w and bh_b <= 0.75 * h:
            # Aspect ratio plausibility: labels are not thin vertical slivers (ar >= 0.50)
            ar_penalty = 1.0 if 0.50 <= ar <= 2.2 else 0.2
            
            # Score based on area, confidence, and aspect ratio
            score = area * float(c) * ar_penalty
            candidates.append((score, b, idx, c))
            
    candidates.sort(key=lambda item: item[0], reverse=True)
    if not candidates:
        print(f"[{name}] No valid label found!")
        return
        
    best_score, best_box, best_idx, best_conf = candidates[0]
    target_box = best_box.astype(int)
    print(f"[{name}] Selected Box: {target_box.tolist()} (conf={best_conf:.2f}, area={target_box[2]-target_box[0]}x{target_box[3]-target_box[1]})")
    
    # Refine with SAM
    mask_sam, score = sam.refine_mask(img, target_box.tolist())
    
    # Clean to single largest component
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
    
    crop_bgr = img[y0:y1, x0:x1].copy()
    crop_mask = mask_sam[y0:y1, x0:x1].copy()
    
    vm = vec.vectorize(crop_mask)
    print(f"  -> Vector Corners: P_TL={vm.P_TL}, P_TR={vm.P_TR}, P_BL={vm.P_BL}, P_BR={vm.P_BR}")
    
    # Vis
    vis = crop_bgr.copy()
    mask_2d = crop_mask > 127
    green_layer = crop_bgr.copy()
    green_layer[mask_2d] = [40, 225, 60]
    vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)
    
    cv2.line(vis, (int(vm.P_TL[0]), int(vm.P_TL[1])), (int(vm.P_BL[0]), int(vm.P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
    cv2.line(vis, (int(vm.P_TR[0]), int(vm.P_TR[1])), (int(vm.P_BR[0]), int(vm.P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [vm.T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [vm.B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    for pt in [vm.P_TL, vm.P_TR, vm.P_BL, vm.P_BR]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)
        
    out_file = rf"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\{name}_verified_vector.png"
    cv2.imwrite(out_file, vis)
    print(f"  -> Saved {out_file}\n")

test_bottle_label_selection("test_dataset/butilki/photo_2026-08-10_12-34-29.jpg", "liria")
test_bottle_label_selection("test_dataset/butilki/photo_2026-08-11_21-10-16.jpg", "alma_valley")
test_bottle_label_selection("test_dataset/butilki/photo_2026-08-10_12-34-30 (2).jpg", "michel")
