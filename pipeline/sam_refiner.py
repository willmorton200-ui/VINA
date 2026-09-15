"""
SAM Refiner: Segment Anything Model Integration for VINA
Refines bounding box prompts (from YOLO) into high-fidelity subpixel instance segmentation masks.
Optimized for NVIDIA RTX 3090 / RTX 3060 CUDA with FP16 Autocast and Local ROI Attention.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple, Union
import cv2
import numpy as np
import torch

logger = logging.getLogger("vina.sam_refiner")

MODELS_DIR = Path(r"D:\models")

class SAMRefiner:
    """
    Refines YOLO bounding boxes into smooth, accurate instance segmentation masks
    using Meta's Segment Anything Model (SAM ViT-H or MobileSAM).
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_type: str = "vit_h",
        device: Optional[str] = None
    ):
        # Default to cuda:0 (RTX 3090 24GB) for maximum compute throughput
        if device is None:
            self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device if torch.cuda.is_available() else "cpu"

        if model_path is None:
            default_vit_h = MODELS_DIR / "sam_vit_h_4b8939.pth"
            default_mobile = MODELS_DIR / "mobile_sam.pt"
            if default_vit_h.exists():
                model_path = str(default_vit_h)
                model_type = "vit_h"
            elif default_mobile.exists():
                model_path = str(default_mobile)
                model_type = "vit_t"
            else:
                model_path = str(default_vit_h)
                model_type = "vit_h"

        self.model_path = Path(model_path)
        self.model_type = model_type
        self.predictor = None
        self._init_model()

    def _init_model(self):
        try:
            from segment_anything import sam_model_registry, SamPredictor
            logger.info(f"[SAMRefiner] Loading SAM ({self.model_type}) on {self.device} from: {self.model_path}")
            if not self.model_path.exists():
                logger.warning(f"[SAMRefiner] Checkpoint not found at {self.model_path}. SAM refinement disabled.")
                return
            
            sam = sam_model_registry[self.model_type](checkpoint=str(self.model_path))
            sam.to(device=self.device)
            # Use eval mode
            sam.eval()
            self.predictor = SamPredictor(sam)
            logger.info(f"[SAMRefiner] SAM ({self.model_type}) loaded successfully on {self.device}.")
        except Exception as e:
            logger.error(f"[SAMRefiner] Failed to load SAM: {e}. Fallback to YOLO mask.")
            self.predictor = None

    def is_ready(self) -> bool:
        return self.predictor is not None

    def refine_mask(
        self,
        img_bgr: np.ndarray,
        bbox_xyxy: Union[list, np.ndarray, tuple],
        point_prompts: Optional[Tuple[np.ndarray, np.ndarray]] = None
    ) -> Tuple[np.ndarray, float]:
        """
        Generates high-precision binary mask inside the bounding box using GPU FP16 acceleration.
        """
        h, w = img_bgr.shape[:2]
        if self.predictor is None:
            mask = np.zeros((h, w), dtype=np.uint8)
            x1, y1, x2, y2 = [int(v) for v in bbox_xyxy]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            mask[y1:y2, x1:x2] = 255
            return mask, 0.5

        # For large images (e.g. 2560x1180), crop localized ROI around bottle to maximize GPU speed
        bx1, by1, bx2, by2 = [int(v) for v in bbox_xyxy]
        bw, bh = max(1, bx2 - bx1), max(1, by2 - by1)
        
        # Generous padding around the bottle
        pad_x = int(bw * 0.25)
        pad_y = int(bh * 0.25)
        roi_x1 = max(0, bx1 - pad_x)
        roi_y1 = max(0, by1 - pad_y)
        roi_x2 = min(w, bx2 + pad_x)
        roi_y2 = min(h, by2 + pad_y)

        roi_bgr = img_bgr[roi_y1:roi_y2, roi_x1:roi_x2]
        roi_rgb = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2RGB)

        # Analyze central paper color vs corner anchors
        cx_local = (bx1 + bx2) // 2 - roi_x1
        cy_local = (by1 + by2) // 2 - roi_y1
        
        roi_lab = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2LAB)
        l_channel = roi_lab[:, :, 0]
        
        c_rad = max(4, int(min(bw, bh) * 0.08))
        cx_c = int(np.clip(cx_local, 0, roi_bgr.shape[1] - 1))
        cy_c = int(np.clip(cy_local, 0, roi_bgr.shape[0] - 1))
        center_patch = l_channel[max(0, cy_c - c_rad):min(roi_bgr.shape[0], cy_c + c_rad),
                                 max(0, cx_c - c_rad):min(roi_bgr.shape[1], cx_c + c_rad)]
        center_L = float(np.median(center_patch)) if center_patch.size > 0 else 128.0

        # Anchor candidates: Center is always positive (label)
        pts_list = [[cx_local, cy_local]]
        labels_list = [1]

        margin_x = int(bw * 0.06)
        margin_y = int(bh * 0.06)
        corner_pts = [
            (bx1 - roi_x1 + margin_x, by1 - roi_y1 + margin_y),
            (bx2 - roi_x1 - margin_x, by1 - roi_y1 + margin_y),
            (bx1 - roi_x1 + margin_x, by2 - roi_y1 - margin_y),
            (bx2 - roi_x1 - margin_x, by2 - roi_y1 - margin_y),
        ]

        for px, py in corner_pts:
            px_c = int(np.clip(px, 0, roi_bgr.shape[1] - 1))
            py_c = int(np.clip(py, 0, roi_bgr.shape[0] - 1))
            pt_L = float(l_channel[py_c, px_c])
            # If corner is significantly darker than center paper (e.g. dark wine/shelf glass),
            # mark it as negative prompt (0) to prevent SAM from spilling into bottle base/shoulders!
            if pt_L < center_L - 35.0 and pt_L < 90.0:
                pts_list.append([px, py])
                labels_list.append(0)
            else:
                pts_list.append([px, py])
                labels_list.append(1)

        pts_local = np.array(pts_list, dtype=np.float32)
        labels_local = np.array(labels_list, dtype=np.int32)

        with torch.no_grad():
            with torch.amp.autocast('cuda', enabled=("cuda" in str(self.device)), dtype=torch.float16):
                self.predictor.set_image(roi_rgb)

                # Local box in ROI coordinate space
                local_box = np.array([bx1 - roi_x1, by1 - roi_y1, bx2 - roi_x1, by2 - roi_y1], dtype=np.float32).reshape(1, 4)
                transformed_boxes = self.predictor.transform.apply_boxes_torch(
                    torch.tensor(local_box, device=self.device),
                    roi_rgb.shape[:2]
                )
                transformed_pts = self.predictor.transform.apply_coords_torch(
                    torch.tensor(pts_local[None, :], device=self.device),
                    roi_rgb.shape[:2]
                )
                labels_tensor = torch.tensor(labels_local[None, :], device=self.device)

                masks, scores, _ = self.predictor.predict_torch(
                    point_coords=transformed_pts,
                    point_labels=labels_tensor,
                    boxes=transformed_boxes,
                    multimask_output=True
                )

        # Pick best scoring mask
        best_mask_idx = torch.argmax(scores[0]).item()
        local_mask = masks[0, best_mask_idx].cpu().numpy().astype(np.uint8) * 255
        score = float(scores[0, best_mask_idx].cpu().numpy()) if scores is not None else 1.0

        # Paste back into full image mask
        full_mask = np.zeros((h, w), dtype=np.uint8)
        full_mask[roi_y1:roi_y2, roi_x1:roi_x2] = local_mask

        return full_mask, score
