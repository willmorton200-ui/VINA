"""
Stage 1: Localization, Segmentation, and Preprocessing
- Multi-bottle detection & Dominant Bottle/Label Selection
- Trained YOLOv8x-seg (Primary: D:\\models\\trained\\antigravity_train\\train_1786971446\\weights\\best.pt)
- YOLO-World v2 Fallback (D:\\models\\yolov8s-worldv2.pt)
- SAM ViT-H Subpixel Instance Mask Refinement (pipeline.sam_refiner)
- Parametric Vector Mask & Shape Classification (pipeline.vectorizer)
- Illumination correction via Multi-Scale Retinex (MSRCR)
- Adaptive local binarization via Sauvola thresholding
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import cv2
import numpy as np
from skimage.filters import threshold_sauvola
import torch

from .sam_refiner import SAMRefiner
from .vectorizer import Vectorizer, VectorMask, LabelShape

TRAINED_WEIGHTS = Path(r"D:\models\trained\antigravity_train\train_1786971446\weights\best.pt")
WORLD_WEIGHTS = Path(r"D:\models\yolov8s-worldv2.pt")
GENERIC_WEIGHTS = Path(r"D:\VINA\yolov8n-seg.pt")

class Stage1Preprocessor:
    def __init__(self, use_gpu: bool = True):
        self.device = "cuda:0" if use_gpu and torch.cuda.is_available() else "cpu"
        self.yolo_model = None
        self.yolo_is_trained = False
        self._init_yolo()
        
        # Initialize SAM refiner (will use cuda:1 if dual GPU, else cuda:0)
        self.sam_refiner = SAMRefiner(device=None)
        self.vectorizer = Vectorizer()

    def _init_yolo(self):
        try:
            from ultralytics import YOLO
            if TRAINED_WEIGHTS.exists():
                print(f"[Stage1] Loading Trained YOLO from {TRAINED_WEIGHTS} on {self.device}...")
                self.yolo_model = YOLO(str(TRAINED_WEIGHTS))
                self.yolo_is_trained = True
                print("[Stage1] Trained YOLO loaded successfully.")
            elif WORLD_WEIGHTS.exists():
                print(f"[Stage1] Loading YOLO-World from {WORLD_WEIGHTS} on {self.device}...")
                self.yolo_model = YOLO(str(WORLD_WEIGHTS))
                self.yolo_model.set_classes(["bottle label", "bottle", "bottle cap", "barcode"])
                self.yolo_is_trained = False
            elif GENERIC_WEIGHTS.exists():
                print(f"[Stage1] Loading generic YOLO from {GENERIC_WEIGHTS} on {self.device}...")
                self.yolo_model = YOLO(str(GENERIC_WEIGHTS))
                self.yolo_is_trained = False
            else:
                self.yolo_model = YOLO("yolov8n-seg.pt")
                self.yolo_is_trained = False
        except Exception as e:
            print(f"[Stage1] YOLO init warning: {e}. Fallback segmentation will be used.")
            self.yolo_model = None
            self.yolo_is_trained = False

    def segment_bottle_and_label(self, img_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
        """
        1. Determines how many bottles are in the photo using YOLO.
        2. Detects bottle_label and bottle instances.
        3. Refines the label mask using SAM ViT-H.
        4. Vectorizes the mask into parametric curves.
        5. Crops the dominant bottle/label.
        """
        h, w = img_bgr.shape[:2]
        img_center = np.array([w / 2.0, h / 2.0])
        img_diag = np.hypot(w, h)
        
        num_bottles = 0
        dominant_label_bbox = None
        dominant_bottle_bbox = None
        yolo_label_mask = None
        yolo_detections = []
        
        # 1. Run YOLO detection
        if self.yolo_model is not None:
            try:
                results = self.yolo_model.predict(img_bgr, verbose=False, device=self.device, conf=0.25)
                for r in results:
                    boxes = r.boxes.xyxy.cpu().numpy() if r.boxes is not None else []
                    confs = r.boxes.conf.cpu().numpy() if r.boxes is not None else []
                    classes = r.boxes.cls.cpu().numpy() if r.boxes is not None else []
                    masks_data = r.masks.data.cpu().numpy() if r.masks is not None else None

                    label_candidates = []
                    bottle_candidates = []

                    for idx, (box, conf, cls_id) in enumerate(zip(boxes, confs, classes)):
                        cls_int = int(cls_id)
                        cls_name = self.yolo_model.names.get(cls_int, f"class_{cls_int}")
                        yolo_detections.append({
                            "class_id": cls_int,
                            "class_name": cls_name,
                            "confidence": float(conf),
                            "box": [int(v) for v in box]
                        })

                        # Check for label (class 0 in trained model or 'label' in name)
                        if cls_int == 0 or "label" in cls_name.lower():
                            label_candidates.append((idx, box, conf))
                        # Check for bottle (class 1 in trained model or 39 in COCO or 'bottle' in name)
                        elif cls_int in (1, 39) or "bottle" in cls_name.lower():
                            bottle_candidates.append((idx, box, conf))

                    num_bottles = max(len(bottle_candidates), 1 if label_candidates else 0)

                    # Filter out mega-boxes (whole-shelf false positives) and thin slivers
                    valid_label_boxes = []
                    for idx, box, conf in label_candidates:
                        bx1, by1, bx2, by2 = box
                        bw_box, bh_box = max(1, bx2 - bx1), max(1, by2 - by1)
                        area = bw_box * bh_box
                        area_ratio = area / float(w * h)
                        ar = bw_box / float(bh_box)
                        
                        # Discard whole-shelf mega boxes and tiny noise
                        if 0.015 <= area_ratio <= 0.55 and bw_box <= 0.70 * w and bh_box <= 0.75 * h:
                            ar_penalty = 1.0 if 0.50 <= ar <= 2.2 else 0.25
                            dist_x = abs((bx1 + bx2) / 2.0 - img_center[0])
                            center_factor = max(0.5, 1.0 - (dist_x / (w * 0.5)))
                            score = area * float(conf) * ar_penalty * center_factor
                            valid_label_boxes.append((score, box, idx, conf))

                    valid_label_boxes.sort(key=lambda item: item[0], reverse=True)

                    if valid_label_boxes:
                        best_score, best_box, best_idx, best_conf = valid_label_boxes[0]
                        dominant_label_bbox = [int(v) for v in best_box]

                    # Pick dominant bottle candidate
                    best_bottle_score = -1.0
                    for idx, box, conf in bottle_candidates:
                        bx1, by1, bx2, by2 = box
                        bw_box, bh_box = max(1, bx2 - bx1), max(1, by2 - by1)
                        area_ratio = (bw_box * bh_box) / float(w * h)
                        if bw_box <= 0.70 * w and area_ratio <= 0.85:
                            dist_x = abs((bx1 + bx2) / 2.0 - img_center[0])
                            center_score = max(0.1, 1.0 - (dist_x / (w * 0.45)))
                            score = center_score * float(conf)
                            if score > best_bottle_score:
                                best_bottle_score = score
                                dominant_bottle_bbox = [int(v) for v in box]
            except Exception as e:
                print(f"[Stage1] YOLO detection error: {e}")

        # 2. Refine Label Mask via SAM ViT-H
        sam_mask = None
        sam_score = 0.0
        target_bbox = dominant_label_bbox or dominant_bottle_bbox

        if target_bbox is not None and self.sam_refiner.is_ready():
            try:
                x1, y1, x2, y2 = target_bbox
                pad_x = int((x2 - x1) * 0.04)
                pad_y = int((y2 - y1) * 0.04)
                prompt_box = [max(0, x1 - pad_x), max(0, y1 - pad_y), min(w, x2 + pad_x), min(h, y2 + pad_y)]
                sam_mask, sam_score = self.sam_refiner.refine_mask(img_bgr, prompt_box)
            except Exception as e:
                print(f"[Stage1] SAM refinement error: {e}")

        # Choose best available mask
        if sam_mask is not None and np.sum(sam_mask > 0) > 0.005 * (h * w):
            label_mask_full = sam_mask
        elif yolo_label_mask is not None:
            label_mask_full = yolo_label_mask
        else:
            # Fallback segmentation
            label_mask_full = self._fallback_segmentation(img_bgr)

        # STRICT FILTER: Retain ONLY the single largest connected component by area
        label_mask_full = self._keep_largest_component(label_mask_full)

        # 3. Determine Bottle Crop Bounding Box covering the label
        coords = cv2.findNonZero(label_mask_full)
        if coords is not None:
            lx, ly, lw, lh = cv2.boundingRect(coords)
            pad_x = int(lw * 0.08)
            pad_y = int(lh * 0.08)
            x0 = max(0, lx - pad_x)
            y0 = max(0, ly - pad_y)
            x1 = min(w, lx + lw + pad_x)
            y1 = min(h, ly + lh + pad_y)
        elif dominant_bottle_bbox is not None:
            cx1, cy1, cx2, cy2 = dominant_bottle_bbox
            pad_x = int((cx2 - cx1) * 0.05)
            pad_y = int((cy2 - cy1) * 0.05)
            x0 = max(0, cx1 - pad_x)
            y0 = max(0, cy1 - pad_y)
            x1 = min(w, cx2 + pad_x)
            y1 = min(h, cy2 + pad_y)
        else:
            x0, y0, x1, y1 = 0, 0, w, h

        cropped_bgr = img_bgr[y0:y1, x0:x1].copy()
        cropped_mask = label_mask_full[y0:y1, x0:x1].copy()
        cropped_mask = self._keep_largest_component(cropped_mask)

        # SOLUTION 3: Photometric Paper Gate (Фильтрация темного стекла и фона)
        cropped_mask = self._apply_photometric_paper_gate(cropped_bgr, cropped_mask)

        # 4. Rectify Bottle Axis: Compute bisector angle between lateral edges and rotate strictly vertical
        ch, cw = cropped_bgr.shape[:2]
        rot_deg = self._compute_axis_bisector_angle(cropped_mask)
        if abs(rot_deg) >= 0.35:
            pivot = (float(cw / 2.0), float(ch / 2.0))
            rot_mat = cv2.getRotationMatrix2D(pivot, rot_deg, 1.0)
            cropped_bgr = cv2.warpAffine(cropped_bgr, rot_mat, (cw, ch), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
            cropped_mask = cv2.warpAffine(cropped_mask, rot_mat, (cw, ch), flags=cv2.INTER_NEAREST)
            cropped_mask = self._keep_largest_component(cropped_mask)

        # 5. Extract Parametric Vector Mask in upright rectified space
        vector_mask = self.vectorizer.extract_vector_mask(cropped_mask, cropped_bgr)

        bbox_info = {
            "num_bottles_detected": max(int(num_bottles), 1),
            "crop_x": int(x0), "crop_y": int(y0), 
            "crop_w": int(x1 - x0), "crop_h": int(y1 - y0),
            "orig_w": int(w), "orig_h": int(h),
            "axis_tilt_deg": float(rot_deg),
            "yolo_detections": yolo_detections,
            "sam_score": float(sam_score),
            "vector_mask": vector_mask
        }

        return cropped_bgr, cropped_mask, bbox_info

    def _compute_axis_bisector_angle(self, mask: np.ndarray) -> float:
        """
        Determines the central bottle axis angle (in degrees) as the angle bisector
        between the left and right lateral boundaries of the mask.
        """
        y_indices, x_indices = np.where(mask > 127)
        if len(y_indices) < 50:
            return 0.0
        y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
        H = y_max - y_min
        
        valid_ys = np.unique(y_indices)
        left_pts = []
        right_pts = []
        for y in valid_ys:
            if y_min + 0.15 * H <= y <= y_max - 0.20 * H:
                col_xs = np.where(mask[y, :] > 127)[0]
                if len(col_xs) > 0:
                    left_pts.append((float(col_xs[0]), float(y)))
                    right_pts.append((float(col_xs[-1]), float(y)))
        if len(left_pts) < 15 or len(right_pts) < 15:
            return 0.0
            
        left_pts = np.array(left_pts)
        right_pts = np.array(right_pts)
        poly_L = np.polyfit(left_pts[:, 1], left_pts[:, 0], deg=1)
        poly_R = np.polyfit(right_pts[:, 1], right_pts[:, 0], deg=1)
        
        theta_L = np.degrees(np.arctan(poly_L[0]))
        theta_R = np.degrees(np.arctan(poly_R[0]))
        theta_axis = (theta_L + theta_R) / 2.0
        return float(theta_axis)

    def _keep_largest_component(self, mask: np.ndarray) -> np.ndarray:
        """
        Retains ONLY the single largest connected component by pixel area.
        All other smaller disconnected mask islands are completely deleted (set to 0).
        """
        if mask is None or np.sum(mask > 127) == 0:
            return mask
        binary = np.uint8(mask > 127)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        if num_labels <= 1:
            return mask
        largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        clean_mask = np.zeros_like(mask)
        clean_mask[labels == largest_label] = 255
        return clean_mask

    def _fallback_segmentation(self, img_bgr: np.ndarray) -> np.ndarray:
        """Saliency & GrabCut based fallback foreground isolation"""
        h, w = img_bgr.shape[:2]
        mask = np.zeros((h, w), dtype=np.uint8)
        margin_x = int(w * 0.08)
        margin_y = int(h * 0.05)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
        
        bgdModel = np.zeros((1, 65), np.float64)
        fgdModel = np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(img_bgr, mask, rect, bgdModel, fgdModel, 3, cv2.GC_INIT_WITH_RECT)
            return np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)
        except Exception:
            mask[margin_y:h - margin_y, margin_x:w - margin_x] = 255
            return mask

    def _guided_filter_mask(self, guide_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Guided filter boundary refinement"""
        gray = cv2.cvtColor(guide_bgr, cv2.COLOR_BGR2GRAY)
        try:
            from cv2.ximgproc import guidedFilter
            return guidedFilter(guide=gray, src=mask, radius=8, eps=1e-2)
        except Exception:
            return cv2.bilateralFilter(mask, 9, 75, 75)

    def enhance_illumination(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Fast Multi-Scale Retinex with Color Restoration (MSRCR) illumination enhancement.
        Optimized with float32 for high throughput.
        """
        img_float = np.float32(img_bgr) + 1.0
        scales = [15, 60, 120]
        weights = [0.333, 0.333, 0.333]
        
        log_img = np.log(img_float)
        retinex = np.zeros_like(img_float, dtype=np.float32)
        for s, w in zip(scales, weights):
            blurred = cv2.GaussianBlur(img_float, (0, 0), s)
            retinex += w * (log_img - np.log(blurred + 1.0))
            
        # Color restoration factor
        img_sum = np.sum(img_float, axis=2, keepdims=True)
        color_rest = np.log(125.0 * img_float) - np.log(img_sum + 1.0)
        msrcr = retinex * color_rest
        
        # Fast percentile clip and normalize
        for c in range(3):
            ch = msrcr[:, :, c]
            c_min = float(np.percentile(ch, 1.0))
            c_max = float(np.percentile(ch, 99.0))
            span = max(c_max - c_min, 1e-4)
            msrcr[:, :, c] = np.clip((ch - c_min) / span * 255.0, 0, 255)
            
        return msrcr.astype(np.uint8)

    def adaptive_binarize(self, enhanced_bgr: np.ndarray, window_size: int = 25, k: float = 0.2) -> np.ndarray:
        """
        Sauvola adaptive local binarization for curved cylinder surfaces with specular glares.
        """
        gray = cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2GRAY)
        thresh_sauvola = threshold_sauvola(gray, window_size=window_size, k=k)
        binary = (gray > thresh_sauvola).astype(np.uint8) * 255
        return binary

    def _apply_photometric_paper_gate(self, img_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Решение 3: Цветовой шлюз (Photometric Paper Gate)
        Фильтрует темное стекло бутылки и блики фона, оставляя строго бумажную наклейку.
        Использует анализ яркости в цветовом пространстве L*a*b* и порог Оцу.
        """
        if mask is None or np.sum(mask > 127) < 100:
            return mask
            
        h, w = mask.shape[:2]
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l_channel = lab[:, :, 0]
        
        # Анализируем пиксели внутри маски
        masked_pixels = l_channel[mask > 127]
        if len(masked_pixels) < 100:
            return mask
            
        # Автоматический порог Оцу внутри маски
        otsu_thresh, _ = cv2.threshold(masked_pixels, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Порог отсечения темного стекла: стекло обычно имеет L < 75-80, бумага L > 110
        glass_cutoff = max(int(otsu_thresh * 0.65), 75)
        
        # Находим верхнюю и нижнюю границы маски
        y_indices, _ = np.where(mask > 127)
        if len(y_indices) == 0:
            return mask
        y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
        H_mask = y_max - y_min
        
        # Отсекаем темное стекло в верхней 35% зоне
        clean_mask = mask.copy()
        top_glass_zone = np.zeros((h, w), dtype=bool)
        top_glass_zone[:int(y_min + H_mask * 0.35), :] = True
        
        clean_mask[top_glass_zone & (l_channel < glass_cutoff)] = 0
        
        # Оставляем только наибольшую связную компоненту (бумажную этикетку)
        clean_mask = self._keep_largest_component(clean_mask)
        
        # Морфологическое закрытие для склеивания внутренних букв
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel)
        
        # Заливка внутренних дыр
        cnts, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            cv2.drawContours(clean_mask, [max(cnts, key=cv2.contourArea)], -1, 255, -1)
            
        return clean_mask

    def process(self, img_bgr: np.ndarray) -> dict:
        """
        Executes full Stage 1 pipeline on input image.
        """
        cropped_bgr, mask, bbox_info = self.segment_bottle_and_label(img_bgr)
        enhanced_bgr = self.enhance_illumination(cropped_bgr)
        binarized = self.adaptive_binarize(enhanced_bgr)

        return {
            "cropped_bgr": cropped_bgr,
            "mask": mask,
            "enhanced_bgr": enhanced_bgr,
            "binarized": binarized,
            "bbox_info": bbox_info,
            "vector_mask": bbox_info.get("vector_mask")
        }
