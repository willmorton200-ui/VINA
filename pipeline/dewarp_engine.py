"""
Master Orchestrator for the 5-Stage Cylindrical Dewarping & OCR Pipeline
"""

import time
import base64
import cv2
import numpy as np
import os
import json

from .stage1_preprocessing import Stage1Preprocessor
from .stage2_features import Stage2FeatureExtractor
from .stage3_optimization import Stage3CylinderOptimizer
from .stage4_remapping import Stage4Remapper
from .stage5_ocr import Stage5OCRDecoder
from .metrics import compute_image_metrics

class CylindricalDewarpEngine:
    def __init__(self, use_gpu: bool = True, languages=['ru', 'en']):
        print("[DewarpEngine] Initializing 5-Stage Pipeline...")
        self.stage1 = Stage1Preprocessor(use_gpu=use_gpu)
        self.stage2 = Stage2FeatureExtractor()
        self.stage3 = Stage3CylinderOptimizer()
        self.stage4 = Stage4Remapper(interpolation_mode="lanczos")
        self.stage5 = Stage5OCRDecoder(languages=languages, use_gpu=use_gpu)
        print("[DewarpEngine] Pipeline initialized successfully.")

    @staticmethod
    def img_to_base64(img_bgr: np.ndarray, quality: int = 88) -> str:
        """Converts an OpenCV BGR image to base64 jpeg data URL string."""
        if img_bgr is None or img_bgr.size == 0:
            return ""
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        success, buffer = cv2.imencode('.jpg', img_bgr, encode_param)
        if not success:
            return ""
        b64_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{b64_str}"

    def process_image(self, 
                      img_bgr: np.ndarray, 
                      reference_bgr: np.ndarray = None,
                      save_dir: str = None) -> dict:
        """
        Executes the entire 5-stage pipeline on the input curved container image.
        """
        start_total = time.time()
        timings = {}
        h_orig, w_orig = img_bgr.shape[:2]

        # ---------------- STAGE 1 ----------------
        t0 = time.time()
        res_s1 = self.stage1.process(img_bgr)
        timings["stage1_ms"] = round((time.time() - t0) * 1000, 1)

        # ---------------- STAGE 2 ----------------
        t0 = time.time()
        res_s2 = self.stage2.process(
            res_s1["binarized"],
            res_s1["enhanced_bgr"], 
            mask=res_s1["mask"],
            vector_mask=res_s1.get("vector_mask")
        )
        timings["stage2_ms"] = round((time.time() - t0) * 1000, 1)

        # ---------------- STAGE 3 ----------------
        t0 = time.time()
        res_s3 = self.stage3.process(
            res_s1["cropped_bgr"],
            res_s2["text_lines"],
            res_s2["line_segments"],
            res_s2["cam_orientation"],
            res_s1["mask"],
            label_boundaries=res_s2.get("label_boundaries")
        )
        timings["stage3_ms"] = round((time.time() - t0) * 1000, 1)

        # ---------------- STAGE 4 ----------------
        t0 = time.time()
        res_s4 = self.stage4.process(res_s1["cropped_bgr"], res_s3)
        timings["stage4_ms"] = round((time.time() - t0) * 1000, 1)

        # ---------------- STAGE 5 ----------------
        t0 = time.time()
        res_s5 = self.stage5.process(res_s4["dewarped_bgr"])
        timings["stage5_ms"] = round((time.time() - t0) * 1000, 1)

        total_ms = round((time.time() - start_total) * 1000, 1)
        timings["total_ms"] = total_ms

        # Compute comparison metrics if reference image is provided
        quality_metrics = {}
        if reference_bgr is not None:
            quality_metrics = compute_image_metrics(res_s4["dewarped_bgr"], reference_bgr)

        # Save to output directory if specified
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            cv2.imwrite(os.path.join(save_dir, "flattened_image.png"), res_s4["dewarped_bgr"])
            cv2.imwrite(os.path.join(save_dir, "stage1_mask.png"), res_s1["mask"])
            cv2.imwrite(os.path.join(save_dir, "stage1_retinex.png"), res_s1["enhanced_bgr"])
            cv2.imwrite(os.path.join(save_dir, "stage1_binarized.png"), res_s1["binarized"])
            cv2.imwrite(os.path.join(save_dir, "stage2_features.png"), res_s2["vis_features"])
            cv2.imwrite(os.path.join(save_dir, "stage3_mesh.png"), res_s3["vis_mesh"])
            cv2.imwrite(os.path.join(save_dir, "stage5_annotated.png"), res_s5["annotated_bgr"])
            
            output_json = {
                "text_blocks": res_s5["text_blocks"],
                "barcodes": res_s5["codes"],
                "full_text": res_s5["full_text"],
                "optimization_params": res_s3["opt_params"],
                "timings": timings,
                "metrics": quality_metrics
            }
            with open(os.path.join(save_dir, "results.json"), "w", encoding="utf-8") as f:
                json.dump(output_json, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "timings": timings,
            "metrics": quality_metrics,
            "text_blocks": res_s5["text_blocks"],
            "barcodes": res_s5["codes"],
            "full_text": res_s5["full_text"],
            "num_words": res_s5["num_words"],
            "opt_params": res_s3["opt_params"],
            "cam_info": res_s2["cam_orientation"],
            "artifacts": {
                "original": self.img_to_base64(img_bgr),
                "cropped": self.img_to_base64(res_s1["cropped_bgr"]),
                "mask": self.img_to_base64(res_s1["mask"]),
                "retinex": self.img_to_base64(res_s1["enhanced_bgr"]),
                "binarized": self.img_to_base64(res_s1["binarized"]),
                "features": self.img_to_base64(res_s2["vis_features"]),
                "mesh": self.img_to_base64(res_s3["vis_mesh"]),
                "dewarped": self.img_to_base64(res_s4["dewarped_bgr"]),
                "annotated": self.img_to_base64(res_s5["annotated_bgr"])
            }
        }
