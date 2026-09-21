"""
Diagnostic: instrument stage1 to save mask at each step.
"""
import cv2
import numpy as np
import sys
import os
import glob

sys.path.insert(0, r"d:\VINA")

out_dir = r"d:\VINA\debug_masks"
os.makedirs(out_dir, exist_ok=True)

# Find image
img_path = r"d:\VINA\test_dataset\cam\757_chteau-le-grand-vostock-le-chene-royal-reserve.jpeg"
print(f"Using: {img_path}")
img_bgr = cv2.imread(img_path)
h, w = img_bgr.shape[:2]
print(f"Image: {w}x{h}")

# Monkey-patch stage1 to save intermediate masks
import pipeline.stage1_preprocessing as s1mod

orig_segment = s1mod.Stage1Preprocessor.segment_bottle_and_label

def instrumented_segment(self, img_bgr):
    h, w = img_bgr.shape[:2]
    
    # Call original up to getting sam_mask
    # Instead, replicate the flow manually with saves
    
    img_center = np.array([w / 2.0, h / 2.0])
    num_bottles = 0
    dominant_label_bbox = None
    yolo_label_mask = None
    
    # YOLO
    if self.yolo_model is not None:
        results = self.yolo_model.predict(img_bgr, conf=0.25, iou=0.5, imgsz=1280, verbose=False, device=self.device)
        for r in results:
            if r.masks is not None and len(r.masks) > 0:
                boxes = r.boxes.xyxy.cpu().numpy()
                confs = r.boxes.conf.cpu().numpy()
                masks_data = r.masks.data.cpu().numpy()
                
                best_idx = int(np.argmax(confs))
                dominant_label_bbox = boxes[best_idx].tolist()
                raw_mask = masks_data[best_idx]
                yolo_label_mask = cv2.resize(raw_mask, (w, h), interpolation=cv2.INTER_LINEAR)
                yolo_label_mask = (yolo_label_mask > 0.5).astype(np.uint8) * 255
    
    if yolo_label_mask is not None:
        cv2.imwrite(os.path.join(out_dir, "01_yolo.png"), yolo_label_mask)
        print(f"[01] YOLO mask: top={np.where(yolo_label_mask>127)[0].min()}")
        print(f"     YOLO bbox: {dominant_label_bbox}")
    
    # SAM
    sam_mask = None
    sam_score = 0.0
    if dominant_label_bbox is not None and self.sam_refiner.is_ready():
        sam_mask, sam_score = self.sam_refiner.refine_mask(img_bgr, dominant_label_bbox)
        if sam_mask is not None:
            cv2.imwrite(os.path.join(out_dir, "02_sam_raw.png"), sam_mask)
            ys = np.where(sam_mask > 127)[0]
            print(f"[02] SAM raw mask: top={ys.min()}, score={sam_score:.4f}")
            
            # Measure top curvature
            top_ys = []
            for x in range(w):
                nz = np.where(sam_mask[:, x] > 127)[0]
                if len(nz) > 0:
                    top_ys.append(nz[0])
            top_ys = np.array(top_ys)
            n = len(top_ys)
            mid = top_ys[n//3:2*n//3]
            edges = np.concatenate([top_ys[:n//6], top_ys[-n//6:]])
            print(f"     SAM top curvature: center_mean={mid.mean():.1f}, edge_mean={edges.mean():.1f}, diff={mid.mean()-edges.mean():.1f}px")
    
    # Selection
    used_sam = False
    if sam_mask is not None and np.sum(sam_mask > 0) > 0.005 * (h * w):
        label_mask = sam_mask.copy()
        used_sam = True
        print(f"[03] Selected: SAM")
    elif yolo_label_mask is not None:
        label_mask = yolo_label_mask.copy()
        print(f"[03] Selected: YOLO")
    
    # Largest component
    label_mask = self._keep_largest_component(label_mask)
    cv2.imwrite(os.path.join(out_dir, "03_largest_comp.png"), label_mask)
    
    # Photometric gate
    label_mask_pg = self._apply_photometric_paper_gate(img_bgr, label_mask.copy())
    cv2.imwrite(os.path.join(out_dir, "04_photometric.png"), label_mask_pg)
    diff = np.sum((label_mask > 127) & (label_mask_pg <= 127))
    print(f"[04] Photometric gate removed {diff} pixels")
    
    # Guided filter
    if not used_sam:
        label_mask_gf = self._guided_filter_mask(img_bgr, label_mask_pg.copy())
        label_mask_gf = (label_mask_gf > 127).astype(np.uint8) * 255
        cv2.imwrite(os.path.join(out_dir, "05_guided_filter.png"), label_mask_gf)
        print(f"[05] Guided filter APPLIED")
    else:
        label_mask_gf = label_mask_pg
        print(f"[05] Guided filter SKIPPED (SAM)")
    
    # Fill scanlines
    label_mask_fs = self._fill_horizontal_scanlines(label_mask_gf.copy())
    cv2.imwrite(os.path.join(out_dir, "06_scanlines.png"), label_mask_fs)
    
    # Morph close
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
    label_mask_mc = cv2.morphologyEx(label_mask_fs, cv2.MORPH_CLOSE, kernel)
    cv2.imwrite(os.path.join(out_dir, "07_morph_close.png"), label_mask_mc)
    
    # Measure final top curvature
    top_ys_f = []
    for x in range(w):
        nz = np.where(label_mask_mc[:, x] > 127)[0]
        if len(nz) > 0:
            top_ys_f.append(nz[0])
    top_ys_f = np.array(top_ys_f)
    n = len(top_ys_f)
    mid = top_ys_f[n//3:2*n//3]
    edges = np.concatenate([top_ys_f[:n//6], top_ys_f[-n//6:]])
    print(f"[07] FINAL top curvature: center={mid.mean():.1f}, edges={edges.mean():.1f}, diff={mid.mean()-edges.mean():.1f}px")
    
    # Now call original for real result
    return orig_segment(self, img_bgr)

s1mod.Stage1Preprocessor.segment_bottle_and_label = instrumented_segment

from pipeline import CylindricalDewarpEngine
engine = CylindricalDewarpEngine(use_gpu=True)
result = engine.process_image(img_bgr)
print(f"\nProcessing complete. Success: {result['success']}")
print(f"Debug masks saved to: {out_dir}")
