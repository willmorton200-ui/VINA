import cv2
import numpy as np
import os
import json
import torch

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer, VectorMask
from pipeline.stage5_ocr import Stage5OCRDecoder
from pipeline.wine_lexicon_corrector import WineVocabularyCorrector

class TwoTierCylindricalEngine:
    def __init__(self, use_gpu: bool = True):
        self.stage1 = Stage1Preprocessor(use_gpu=use_gpu)
        self.vectorizer = MaskVectorizer()
        self.stage5 = Stage5OCRDecoder(use_gpu=use_gpu)
        self.lexicon = WineVocabularyCorrector()

    def _dewarp_single_tier(self, img_crop: np.ndarray, mask: np.ndarray):
        """Vectorizes and dewarps a single label tier using 3D Coon's patch."""
        h_c, w_c = img_crop.shape[:2]
        
        # 1. Strict Corners
        vec_init = self.vectorizer.vectorize(mask)
        
        # 2. Bisector verticalization
        v_L = vec_init.P_BL - vec_init.P_TL
        v_R = vec_init.P_BR - vec_init.P_TR
        u_L = v_L / max(np.hypot(v_L[0], v_L[1]), 1e-4)
        u_R = v_R / max(np.hypot(v_R[0], v_R[1]), 1e-4)
        b_vec = u_L + u_R
        b_vec /= max(np.hypot(b_vec[0], b_vec[1]), 1e-4)
        theta = float(np.degrees(np.arctan2(b_vec[0], b_vec[1])))
        
        if abs(theta) >= 0.25:
            pivot = (float(w_c / 2.0), float(h_c / 2.0))
            rot_mat = cv2.getRotationMatrix2D(pivot, theta, 1.0)
            rot_img = cv2.warpAffine(img_crop, rot_mat, (w_c, h_c), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
            rot_mask = cv2.warpAffine(mask, rot_mat, (w_c, h_c), flags=cv2.INTER_NEAREST)
            rot_mask = self.stage1._keep_largest_component(rot_mask)
        else:
            rot_img = img_crop
            rot_mask = mask
            
        vec = self.vectorizer.vectorize(rot_mask)
        
        # 3. 3D Coon's grid
        grid_rows, grid_cols = 24, 32
        u_g = np.linspace(0.0, 1.0, grid_cols)
        v_g = np.linspace(0.0, 1.0, grid_rows)
        u_vals = np.linspace(0.0, 1.0, len(vec.T_curve))
        v_vals = np.linspace(0.0, 1.0, len(vec.L_line))
        
        T_res = np.column_stack((np.interp(u_g, u_vals, vec.T_curve[:, 0]), np.interp(u_g, u_vals, vec.T_curve[:, 1])))
        B_res = np.column_stack((np.interp(u_g, u_vals, vec.B_curve[:, 0]), np.interp(u_g, u_vals, vec.B_curve[:, 1])))
        L_res = np.column_stack((np.interp(v_g, v_vals, vec.L_line[:, 0]), np.interp(v_g, v_vals, vec.L_line[:, 1])))
        R_res = np.column_stack((np.interp(v_g, v_vals, vec.R_line[:, 0]), np.interp(v_g, v_vals, vec.R_line[:, 1])))
        
        u_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
        v_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
        for r in range(grid_rows):
            v_val = v_g[r]
            for c in range(grid_cols):
                u_val = u_g[c]
                c_blend = (1.0 - u_val)*(1.0 - v_val)*vec.P_TL + u_val*(1.0 - v_val)*vec.P_TR + (1.0 - u_val)*v_val*vec.P_BL + u_val*v_val*vec.P_BR
                pt = (1.0 - v_val)*T_res[c] + v_val*B_res[c] + (1.0 - u_val)*L_res[r] + u_val*R_res[r] - c_blend
                u_grid[r, c] = np.clip(pt[0], 0, w_c - 1)
                v_grid[r, c] = np.clip(pt[1], 0, h_c - 1)
                
        arc_T = np.sum(np.hypot(np.diff(vec.T_curve[:, 0]), np.diff(vec.T_curve[:, 1])))
        arc_B = np.sum(np.hypot(np.diff(vec.B_curve[:, 0]), np.diff(vec.B_curve[:, 1])))
        dst_w = max(int(round(max(arc_T, arc_B))), 100)
        
        len_L = np.sum(np.hypot(np.diff(vec.L_line[:, 0]), np.diff(vec.L_line[:, 1])))
        len_R = np.sum(np.hypot(np.diff(vec.R_line[:, 0]), np.diff(vec.R_line[:, 1])))
        dst_h = max(int(round(max(len_L, len_R))), 100)
        
        map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        dewarped = cv2.remap(rot_img, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
        
        # 4. OCR
        ocr_res = self.stage5.process(dewarped)
        return {
            "dewarped": dewarped,
            "rot_crop": rot_img,
            "rot_mask": rot_mask,
            "vector_mask": vec,
            "ocr": ocr_res
        }

    def process_bottle(self, img_bgr: np.ndarray):
        """
        Detects if the dominant bottle contains a 2-tier composite label (Upper + Lower)
        or a standard single solid label, and transforms each tier independently.
        """
        h_orig, w_orig = img_bgr.shape[:2]
        
        # 1. Segment using YOLOv8x-seg
        yolo_res = self.stage1.yolo_model.predict(img_bgr, verbose=False, device=self.stage1.device, conf=0.20)
        
        # Collect candidate label masks on the central bottle
        label_components = []
        if yolo_res[0].masks is not None:
            boxes = yolo_res[0].boxes.xyxy.cpu().numpy()
            classes = yolo_res[0].boxes.cls.cpu().numpy()
            confs = yolo_res[0].boxes.conf.cpu().numpy()
            
            img_cx = w_orig / 2.0
            for idx, (box, cls_id, conf) in enumerate(zip(boxes, classes, confs)):
                cls_int = int(cls_id)
                cls_name = self.stage1.yolo_model.names.get(cls_int, f"class_{cls_int}").lower()
                if cls_int == 0 or "label" in cls_name:
                    bx1, by1, bx2, by2 = [int(v) for v in box]
                    bcx = (bx1 + bx2) / 2.0
                    bw, bh = bx2 - bx1, by2 - by1
                    area = bw * bh
                    
                    # Must be near center of photo (main bottle) and reasonable size
                    if abs(bcx - img_cx) <= 0.35 * w_orig and area >= 0.015 * (w_orig * h_orig):
                        m_raw = yolo_res[0].masks.data[idx].cpu().numpy()
                        mask_full = (cv2.resize(m_raw, (w_orig, h_orig)) > 0.5).astype(np.uint8) * 255
                        label_components.append({
                            "box": [bx1, by1, bx2, by2],
                            "area": area,
                            "y_center": (by1 + by2) / 2.0,
                            "mask": mask_full
                        })

        # Check if we have 2 vertically stacked labels on the main bottle
        if len(label_components) >= 2:
            # Sort by area descending to find the top 2 candidate labels on this bottle
            label_components.sort(key=lambda x: x["area"], reverse=True)
            top2 = label_components[:2]
            
            # Check vertical alignment (same X column)
            c1_x = (top2[0]["box"][0] + top2[0]["box"][2]) / 2.0
            c2_x = (top2[1]["box"][0] + top2[1]["box"][2]) / 2.0
            w_avg = (top2[0]["box"][2] - top2[0]["box"][0] + top2[1]["box"][2] - top2[1]["box"][0]) / 2.0
            
            # If horizontally aligned along the same bottle axis (|dx| <= 0.35 * w)
            if abs(c1_x - c2_x) <= 0.35 * w_avg:
                # Sort top to bottom
                top2.sort(key=lambda x: x["y_center"])
                lbl_upper = top2[0]
                lbl_lower = top2[1]
                
                print(f"[2-Tier Mode Active]: Found 2-Tier Stack (Upper at y={lbl_upper['y_center']:.0f}, Lower at y={lbl_lower['y_center']:.0f})")
                
                # Process Upper Tier
                ux1, uy1, ux2, uy2 = lbl_upper["box"]
                pad_u = int((ux2 - ux1) * 0.06)
                crop_u = img_bgr[max(0, uy1-pad_u):min(h_orig, uy2+pad_u), max(0, ux1-pad_u):min(w_orig, ux2+pad_u)]
                mask_u = lbl_upper["mask"][max(0, uy1-pad_u):min(h_orig, uy2+pad_u), max(0, ux1-pad_u):min(w_orig, ux2+pad_u)]
                mask_u = self.stage1._apply_photometric_paper_gate(crop_u, mask_u)
                mask_u = self.stage1._keep_largest_component(mask_u)
                res_upper = self._dewarp_single_tier(crop_u, mask_u)
                
                # Process Lower Tier
                lx1, ly1, lx2, ly2 = lbl_lower["box"]
                pad_l = int((lx2 - lx1) * 0.06)
                crop_l = img_bgr[max(0, ly1-pad_l):min(h_orig, ly2+pad_l), max(0, lx1-pad_l):min(w_orig, lx2+pad_l)]
                mask_l = lbl_lower["mask"][max(0, ly1-pad_l):min(h_orig, ly2+pad_l), max(0, lx1-pad_l):min(w_orig, lx2+pad_l)]
                mask_l = self.stage1._apply_photometric_paper_gate(crop_l, mask_l)
                mask_l = self.stage1._keep_largest_component(mask_l)
                res_lower = self._dewarp_single_tier(crop_l, mask_l)
                
                # Stack into 2-Tier Composite Panel
                scan_u = res_upper["dewarped"]
                scan_l = res_lower["dewarped"]
                max_w = max(scan_u.shape[1], scan_l.shape[1])
                
                def pad_w(im):
                    if im.shape[1] == max_w: return im
                    diff = max_w - im.shape[1]
                    return cv2.copyMakeBorder(im, 0, 0, 0, diff, cv2.BORDER_CONSTANT, value=[30, 30, 30])
                    
                sep = np.zeros((18, max_w, 3), dtype=np.uint8) + 40
                composite_dewarped = np.vstack((pad_w(scan_u), sep, pad_w(scan_l)))
                composite_annotated = np.vstack((pad_w(res_upper["ocr"]["annotated_bgr"]), sep, pad_w(res_lower["ocr"]["annotated_bgr"])))
                
                all_text_blocks = res_upper["ocr"]["text_blocks"] + res_lower["ocr"]["text_blocks"]
                full_text = f"[ВЕРХНИЙ ЯРУС]: {res_upper['ocr']['full_text']}\n[НИЖНИЙ ЯРУС]: {res_lower['ocr']['full_text']}"
                
                return {
                    "is_two_tier": True,
                    "dewarped": composite_dewarped,
                    "annotated": composite_annotated,
                    "upper_tier": res_upper,
                    "lower_tier": res_lower,
                    "text_blocks": all_text_blocks,
                    "full_text": full_text
                }
                    
        # Single solid label default
        raw_crop, raw_mask, _ = self.stage1.segment_bottle_and_label(img_bgr)
        raw_mask = self.stage1._apply_photometric_paper_gate(raw_crop, raw_mask)
        raw_mask = self.stage1._keep_largest_component(raw_mask)
        
        print("[Single Tier Mode]: Transforming single dominant label...")
        res_single = self._dewarp_single_tier(raw_crop, raw_mask)
        return {
            "is_two_tier": False,
            "dewarped": res_single["dewarped"],
            "annotated": res_single["ocr"]["annotated_bgr"],
            "single_tier": res_single,
            "text_blocks": res_single["ocr"]["text_blocks"],
            "full_text": res_single["ocr"]["full_text"]
        }

if __name__ == "__main__":
    engine = TwoTierCylindricalEngine(use_gpu=True)
    
    # 1. Test on Barakiani (2-tier)
    img_b = cv2.imread("test_dataset/butilki/photo_2026-08-10_12-34-31.jpg")
    res_b = engine.process_bottle(img_b)
    print("\n--- BARAKIANI RESULTS ---")
    print("Is Two-Tier:", res_b["is_two_tier"])
    print("Full Text:\n", res_b["full_text"])
    
    # 2. Test on Tempranillo (single tier)
    img_t = cv2.imread("test_dataset/butilki/photo_2026-08-11_21-10-14.jpg")
    res_t = engine.process_bottle(img_t)
    print("\n--- TEMPRANILLO RESULTS ---")
    print("Is Two-Tier:", res_t["is_two_tier"])
    print("Full Text:\n", res_t["full_text"])
