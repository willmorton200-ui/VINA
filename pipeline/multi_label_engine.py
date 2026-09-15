import cv2
import numpy as np
import os
import json
import torch
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional

from pipeline.stage1_preprocessing import Stage1Preprocessor
from pipeline.vectorizer import MaskVectorizer, VectorMask
from pipeline.stage5_ocr import Stage5OCRDecoder

@dataclass
class LabelResult:
    label_id: int
    label_type: str  # 'collar', 'main', 'lower', 'label'
    bbox_orig: List[int]
    crop_bgr: np.ndarray
    mask_bgr: np.ndarray
    dewarped_bgr: np.ndarray
    vector_mask: VectorMask
    bisector_angle_deg: float
    raw_ocr: Dict[str, Any]
    dewarped_ocr: Dict[str, Any]
    gain_words: int
    transformation_status: str  # 'SUCCESS', 'EXACT', 'FAILED'

@dataclass
class BottleResult:
    bottle_id: int
    bottle_bbox: List[int]
    labels: List[LabelResult] = field(default_factory=list)
    consolidated_text: str = ""
    total_raw_words: int = 0
    total_dewarped_words: int = 0
    total_gain_words: int = 0
    overall_status: str = "EXACT"

class MultiLabelBottleEngine:
    def __init__(self, use_gpu: bool = True):
        self.stage1 = Stage1Preprocessor(use_gpu=use_gpu)
        self.vectorizer = MaskVectorizer()
        self.ocr_decoder = Stage5OCRDecoder(use_gpu=use_gpu)

    def process_image(self, img_bgr: np.ndarray) -> List[BottleResult]:
        """
        1. Detects all bottles and labels via YOLO.
        2. Groups labels belonging to the same bottle along their vertical bisector axis.
        3. Sorts labels for each bottle strictly from top to bottom.
        4. Rectifies each label so its lateral bisector is strictly vertical (90 deg).
        5. Dewarps each label independently via 3D Coon's patch grid.
        6. Runs dual OCR (before vs after dewarping) and evaluates word counts.
        7. Produces consolidated bottle text with individual label breakdown.
        """
        h_orig, w_orig = img_bgr.shape[:2]
        
        # 1. Run YOLO to get all bottle and label candidate boxes
        yolo_res = self.stage1.yolo_model.predict(img_bgr, verbose=False, device=self.stage1.device, conf=0.20)
        
        bottle_boxes = []
        label_boxes = []
        
        for r in yolo_res:
            boxes = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else []
            confs = r.boxes.conf.cpu().numpy() if r.boxes is not None else []
            classes = r.boxes.cls.cpu().numpy() if r.boxes is not None else []
            
            for box, conf, cls_id in zip(boxes, confs, classes):
                cls_int = int(cls_id)
                cls_name = self.stage1.yolo_model.names.get(cls_int, f"class_{cls_int}").lower()
                bx1, by1, bx2, by2 = [int(v) for v in box]
                bw, bh = bx2 - bx1, by2 - by1
                area = bw * bh
                
                # Check for bottle
                if cls_int in (1, 39) or "bottle" in cls_name and "label" not in cls_name:
                    if bw <= 0.85 * w_orig and area >= 0.05 * (w_orig * h_orig):
                        bottle_boxes.append((box, float(conf)))
                # Check for label
                elif cls_int == 0 or "label" in cls_name:
                    # Filter out whole-shelf mega-boxes and tiny noise
                    if 0.008 <= (area / float(w_orig * h_orig)) <= 0.60 and bw <= 0.75 * w_orig and bh <= 0.80 * h_orig:
                        label_boxes.append((box, float(conf)))
                        
        # Non-Maximum Suppression on label boxes to remove duplicate detections
        label_boxes = self._nms_boxes(label_boxes, iou_thresh=0.45)
        
        # If no bottle box found, construct default bottle boxes covering label clusters
        if not bottle_boxes:
            if label_boxes:
                # Group labels into vertical bottle clusters
                clusters = self._cluster_labels_into_bottles(label_boxes, w_orig)
                for cluster in clusters:
                    cbx1 = min(int(b[0][0]) for b in cluster)
                    cby1 = min(int(b[0][1]) for b in cluster)
                    cbx2 = max(int(b[0][2]) for b in cluster)
                    cby2 = max(int(b[0][3]) for b in cluster)
                    pad_w = int((cbx2 - cbx1) * 0.15)
                    pad_h = int((cby2 - cby1) * 0.15)
                    bottle_boxes.append((np.array([max(0, cbx1 - pad_w), max(0, cby1 - pad_h), min(w_orig, cbx2 + pad_w), min(h_orig, cby2 + pad_h)]), 1.0))
            else:
                bottle_boxes.append((np.array([0, 0, w_orig, h_orig]), 1.0))
                
        # 2. Group labels to their parent bottle by horizontal axis alignment
        bottle_results = []
        
        for b_idx, (b_box, b_conf) in enumerate(bottle_boxes):
            bx1, by1, bx2, by2 = [int(v) for v in b_box]
            b_cx = (bx1 + bx2) / 2.0
            b_width = bx2 - bx1
            
            # Find labels belonging to this bottle
            matched_labels = []
            for l_box, l_conf in label_boxes:
                lx1, ly1, lx2, ly2 = [int(v) for v in l_box]
                l_cx = (lx1 + lx2) / 2.0
                # Match condition: label center is within horizontal tolerance of bottle axis
                if abs(l_cx - b_cx) <= 0.40 * b_width and (ly1 >= by1 - 50 and ly2 <= by2 + 50):
                    matched_labels.append((l_box, l_conf))
                    
            if not matched_labels:
                # If no specific sub-label detected, use bottle crop as single label
                matched_labels.append((b_box, b_conf))
                
            # 3. SORT LABELS STRICTLY TOP-TO-BOTTOM (by Y center)
            matched_labels.sort(key=lambda item: (item[0][1] + item[0][3]) / 2.0)
            
            # Process each label of this bottle
            label_results = []
            consolidated_texts = []
            total_raw_w = 0
            total_dew_w = 0
            
            for l_idx, (l_box, l_conf) in enumerate(matched_labels):
                lx1, ly1, lx2, ly2 = [int(v) for v in l_box]
                
                # Determine label type based on vertical rank
                if len(matched_labels) > 1:
                    if l_idx == 0 and ly1 < by1 + 0.35 * (by2 - by1):
                        l_type = "Кольеретка (Верхняя)"
                    elif l_idx == len(matched_labels) - 1:
                        l_type = "Нижняя этикетка"
                    else:
                        l_type = f"Основная этикетка #{l_idx+1}"
                else:
                    l_type = "Основная этикетка"
                    
                # SAM Mask Refinement
                pad_x = int((lx2 - lx1) * 0.05)
                pad_y = int((ly2 - ly1) * 0.05)
                crop_x1 = max(0, lx1 - pad_x)
                crop_y1 = max(0, ly1 - pad_y)
                crop_x2 = min(w_orig, lx2 + pad_x)
                crop_y2 = min(h_orig, ly2 + pad_y)
                
                mask_full, _ = self.stage1.sam_refiner.refine_mask(img_bgr, [lx1, ly1, lx2, ly2])
                crop_bgr = img_bgr[crop_y1:crop_y2, crop_x1:crop_x2].copy()
                mask_crop = mask_full[crop_y1:crop_y2, crop_x1:crop_x2].copy()
                
                # Filter largest component
                mask_crop = self.stage1._keep_largest_component(mask_crop)
                
                # Initial vectorization to find lateral generators
                vec_init = self.vectorizer.vectorize(mask_crop)
                
                # 4. STRICT BISECTOR VERTICALIZATION
                # Compute bisector angle between lateral guides and rotate upright
                bisector_deg, rot_crop_bgr, rot_mask = self._verticalize_bisector(
                    crop_bgr, mask_crop, vec_init.P_TL, vec_init.P_TR, vec_init.P_BL, vec_init.P_BR
                )
                
                # Re-vectorize in strictly vertical coordinate frame
                vec_rectified = self.vectorizer.vectorize(rot_mask)
                
                # 5. 3D Coon's Patch Dewarping
                dewarped_bgr = self._dewarp_coons_patch(rot_crop_bgr, vec_rectified)
                
                # 6. DUAL OCR VERIFICATION (Raw Crop vs Dewarped Scan)
                ocr_raw = self.ocr_decoder.process(rot_crop_bgr)
                ocr_dew = self.ocr_decoder.process(dewarped_bgr)
                
                n_raw = len(ocr_raw["text_blocks"])
                n_dew = len(ocr_dew["text_blocks"])
                gain = n_dew - n_raw
                
                if gain > 0:
                    status = f"+{gain} сл (прирост)"
                elif gain < 0:
                    status = f"{gain} сл (неудачная трансформация)"
                else:
                    status = "0 (без изменений)"
                    
                total_raw_w += n_raw
                total_dew_w += n_dew
                
                if ocr_dew["full_text"].strip():
                    consolidated_texts.append(f"[{l_type.upper()}]: {ocr_dew['full_text'].strip()}")
                elif ocr_raw["full_text"].strip():
                    consolidated_texts.append(f"[{l_type.upper()}]: {ocr_raw['full_text'].strip()}")
                    
                label_results.append(LabelResult(
                    label_id=l_idx + 1,
                    label_type=l_type,
                    bbox_orig=[lx1, ly1, lx2, ly2],
                    crop_bgr=rot_crop_bgr,
                    mask_bgr=rot_mask,
                    dewarped_bgr=dewarped_bgr,
                    vector_mask=vec_rectified,
                    bisector_angle_deg=bisector_deg,
                    raw_ocr=ocr_raw,
                    dewarped_ocr=ocr_dew,
                    gain_words=gain,
                    transformation_status=status
                ))
                
            bottle_gain = total_dew_w - total_raw_w
            if bottle_gain > 0:
                b_status = f"+{bottle_gain} сл (успешная трансформация)"
            elif bottle_gain < 0:
                b_status = f"{bottle_gain} сл (неудачная трансформация)"
            else:
                b_status = "0 (без изменений)"
                
            bottle_results.append(BottleResult(
                bottle_id=b_idx + 1,
                bottle_bbox=[bx1, by1, bx2, by2],
                labels=label_results,
                consolidated_text="\n".join(consolidated_texts),
                total_raw_words=total_raw_w,
                total_dewarped_words=total_dew_w,
                total_gain_words=bottle_gain,
                overall_status=b_status
            ))
            
        return bottle_results

    def _verticalize_bisector(
        self,
        img: np.ndarray,
        mask: np.ndarray,
        P_TL: np.ndarray,
        P_TR: np.ndarray,
        P_BL: np.ndarray,
        P_BR: np.ndarray
    ) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Computes the central angle bisector between the left lateral guide (P_TL -> P_BL)
        and right lateral guide (P_TR -> P_BR) and rotates the image so the bisector is exactly vertical.
        """
        # Direction vectors
        v_L = P_BL - P_TL
        v_R = P_BR - P_TR
        
        n_L = max(np.hypot(v_L[0], v_L[1]), 1e-4)
        n_R = max(np.hypot(v_R[0], v_R[1]), 1e-4)
        
        u_L = v_L / n_L
        u_R = v_R / n_R
        
        # Angle bisector unit vector
        b_vec = u_L + u_R
        n_b = max(np.hypot(b_vec[0], b_vec[1]), 1e-4)
        b_vec /= n_b
        
        # Angle with strictly vertical direction [0, 1]
        # theta = arctan2(bx, by)
        theta_rad = np.arctan2(b_vec[0], b_vec[1])
        theta_deg = float(np.degrees(theta_rad))
        
        ch, cw = img.shape[:2]
        if abs(theta_deg) >= 0.25:
            pivot = (float(cw / 2.0), float(ch / 2.0))
            rot_mat = cv2.getRotationMatrix2D(pivot, theta_deg, 1.0)
            rot_img = cv2.warpAffine(img, rot_mat, (cw, ch), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
            rot_mask = cv2.warpAffine(mask, rot_mat, (cw, ch), flags=cv2.INTER_NEAREST)
            rot_mask = self.stage1._keep_largest_component(rot_mask)
            return theta_deg, rot_img, rot_mask
        else:
            return 0.0, img, mask

    def _dewarp_coons_patch(self, img_bgr: np.ndarray, vec: VectorMask) -> np.ndarray:
        """
        Performs 3D Coon's patch grid optimization and dense Lanczos-4 remap.
        """
        h_c, w_c = img_bgr.shape[:2]
        T_curve, B_curve = vec.T_curve, vec.B_curve
        L_line, R_line = vec.L_line, vec.R_line
        P_TL, P_TR, P_BL, P_BR = vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR
        
        grid_rows, grid_cols = 24, 32
        u_g = np.linspace(0.0, 1.0, grid_cols)
        v_g = np.linspace(0.0, 1.0, grid_rows)
        
        u_vals = np.linspace(0.0, 1.0, len(T_curve))
        v_vals = np.linspace(0.0, 1.0, len(L_line))
        
        T_res = np.column_stack((np.interp(u_g, u_vals, T_curve[:, 0]), np.interp(u_g, u_vals, T_curve[:, 1])))
        B_res = np.column_stack((np.interp(u_g, u_vals, B_curve[:, 0]), np.interp(u_g, u_vals, B_curve[:, 1])))
        L_res = np.column_stack((np.interp(v_g, v_vals, L_line[:, 0]), np.interp(v_g, v_vals, L_line[:, 1])))
        R_res = np.column_stack((np.interp(v_g, v_vals, R_line[:, 0]), np.interp(v_g, v_vals, R_line[:, 1])))
        
        u_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
        v_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
        
        for r in range(grid_rows):
            v_val = v_g[r]
            for c in range(grid_cols):
                u_val = u_g[c]
                c_blend = (1.0 - u_val)*(1.0 - v_val)*P_TL + u_val*(1.0 - v_val)*P_TR + (1.0 - u_val)*v_val*P_BL + u_val*v_val*P_BR
                pt = (1.0 - v_val)*T_res[c] + v_val*B_res[c] + (1.0 - u_val)*L_res[r] + u_val*R_res[r] - c_blend
                u_grid[r, c] = np.clip(pt[0], 0, w_c - 1)
                v_grid[r, c] = np.clip(pt[1], 0, h_c - 1)
                
        arc_T = np.sum(np.hypot(np.diff(T_curve[:, 0]), np.diff(T_curve[:, 1])))
        arc_B = np.sum(np.hypot(np.diff(B_curve[:, 0]), np.diff(B_curve[:, 1])))
        dst_w = max(int(round(max(arc_T, arc_B))), 100)
        
        len_L = np.sum(np.hypot(np.diff(L_line[:, 0]), np.diff(L_line[:, 1])))
        len_R = np.sum(np.hypot(np.diff(R_line[:, 0]), np.diff(R_line[:, 1])))
        dst_h = max(int(round(max(len_L, len_R))), 100)
        
        map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        dewarped = cv2.remap(img_bgr, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
        return dewarped

    def _nms_boxes(self, boxes_with_conf: List[Tuple[np.ndarray, float]], iou_thresh: float = 0.45):
        if not boxes_with_conf:
            return []
        boxes_with_conf.sort(key=lambda item: item[1], reverse=True)
        keep = []
        while boxes_with_conf:
            curr = boxes_with_conf.pop(0)
            keep.append(curr)
            boxes_with_conf = [
                b for b in boxes_with_conf if self._compute_iou(curr[0], b[0]) < iou_thresh
            ]
        return keep

    @staticmethod
    def _compute_iou(b1, b2):
        x1 = max(b1[0], b2[0])
        y1 = max(b1[1], b2[1])
        x2 = min(b1[2], b2[2])
        y2 = min(b1[3], b2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        area2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        union = area1 + area2 - inter
        return inter / max(union, 1e-6)

    def _cluster_labels_into_bottles(self, label_boxes, img_w):
        """Groups label bounding boxes that align vertically along the same axis."""
        clusters = []
        for l in label_boxes:
            box = l[0]
            l_cx = (box[0] + box[2]) / 2.0
            matched = False
            for cluster in clusters:
                c_cx = np.mean([(b[0][0] + b[0][2]) / 2.0 for b in cluster])
                c_w = np.mean([(b[0][2] - b[0][0]) for b in cluster])
                if abs(l_cx - c_cx) <= 0.35 * c_w:
                    cluster.append(l)
                    matched = True
                    break
            if not matched:
                clusters.append([l])
        return clusters
