"""
Master Orchestrator for the VINA Cylindrical Dewarping & OCR Pipeline
Features:
- Single Dominant Label Localization (Largest Connected Component by Area)
- Dual Verification & Comparative Selection (Raw Crop vs Dewarped Scan)
- Automated Intelligent Selection based on Word Count Completeness
- Regularized Coon's Patch Meshing to Prevent Font Proportion Distortions
- Bisector Strict Verticalization (90.0° vertical bottle axis)
- RapidOCR (PP-OCRv4 ONNX GPU) + Domain Wine Lexicon Auto-Correction
- High-Speed Performance on RTX 3090 / CUDA
"""

import time
import base64
import cv2
import numpy as np
import os
import json
import torch

from .stage1_preprocessing import Stage1Preprocessor
from .vectorizer import MaskVectorizer, VectorMask
from .stage5_ocr import Stage5OCRDecoder
from .wine_lexicon_corrector import WineVocabularyCorrector
from .metrics import compute_image_metrics

class CylindricalDewarpEngine:
    def __init__(self, use_gpu: bool = True, languages=['ru', 'en'], ocr_engine: str = "vlm"):
        print(f"[DewarpEngine] Initializing Production Dewarping Engine (OCR: {ocr_engine.upper()})...")
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = "cuda:0" if self.use_gpu else "cpu"
        self.ocr_engine = ocr_engine
        
        self.stage1 = Stage1Preprocessor(use_gpu=use_gpu)
        self.vectorizer = MaskVectorizer()
        self.stage5 = Stage5OCRDecoder(languages=languages, use_gpu=use_gpu, primary_engine=ocr_engine)
        self.lexicon = WineVocabularyCorrector()
        print("[DewarpEngine] Production Engine ready.")

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

    def _dewarp_single_tier(self, img_crop: np.ndarray, mask: np.ndarray) -> dict:
        """Vectorizes and dewarps a single label using regularized 3D Coon's patch."""
        h_c, w_c = img_crop.shape[:2]
        
        # 1. OCR on Raw Crop (only needed in classic dual-verification mode; skipped in VLM mode)
        if self.ocr_engine == "vlm":
            ocr_raw = {"text_blocks": [], "full_text": "", "annotated_bgr": img_crop, "codes": []}
            t_ocr_raw_ms = 0.0
            t_s2_0 = time.perf_counter()
            vec = self.vectorizer.extract_vector_mask(mask, ocr_data=None, image=img_crop)
            stage2_ms = (time.perf_counter() - t_s2_0) * 1000.0
        else:
            t_ocr_raw_0 = time.perf_counter()
            ocr_raw = self.stage5.process(img_crop)
            t_ocr_raw_ms = (time.perf_counter() - t_ocr_raw_0) * 1000.0
            t_s2_0 = time.perf_counter()
            vec = self.vectorizer.extract_vector_mask(mask, ocr_data=ocr_raw, image=img_crop)
            stage2_ms = (time.perf_counter() - t_s2_0) * 1000.0
        
        # 3. Compute bisector angle for telemetry/diagnostics
        t_s3_0 = time.perf_counter()
        v_L = vec.P_BL - vec.P_TL
        v_R = vec.P_BR - vec.P_TR
        u_L = v_L / max(np.hypot(v_L[0], v_L[1]), 1e-4)
        u_R = v_R / max(np.hypot(v_R[0], v_R[1]), 1e-4)
        b_vec = u_L + u_R
        b_vec /= max(np.hypot(b_vec[0], b_vec[1]), 1e-4)
        theta = float(np.degrees(np.arctan2(b_vec[0], b_vec[1])))
        
        rot_img = img_crop
        rot_mask = mask
        
        # Ensure canvas has sufficient bottom padding if reconstructed B_curve extends downwards
        max_y_curve = float(np.max(vec.B_curve[:, 1]))
        if max_y_curve >= h_c - 1:
            pad_bot_needed = int(np.ceil(max_y_curve - (h_c - 1))) + 20
            rot_img = cv2.copyMakeBorder(rot_img, 0, pad_bot_needed, 0, 0, borderType=cv2.BORDER_REPLICATE)
            rot_mask = cv2.copyMakeBorder(rot_mask, 0, pad_bot_needed, 0, 0, borderType=cv2.BORDER_CONSTANT, value=0)
            h_c, w_c = rot_img.shape[:2]
        
        # 4. VINA 3.0: Artist Strokes Parameterization (Multi-segment Coon's Patch)
        grid_cols = 32
        u_norm_prof = np.linspace(0.0, 1.0, grid_cols)
        
        # 1. Извлекаем RANSAC-направляющие
        dx_L = vec.L_line[-1, 0] - vec.L_line[0, 0]
        dy_L = vec.L_line[-1, 1] - vec.L_line[0, 1]
        m_L = dx_L / dy_L if abs(dy_L) > 1e-5 else 0.0
        X_L0, Y_L0 = vec.L_line[0, 0], vec.L_line[0, 1]
        
        dx_R = vec.R_line[-1, 0] - vec.R_line[0, 0]
        dy_R = vec.R_line[-1, 1] - vec.R_line[0, 1]
        m_R = dx_R / dy_R if abs(dy_R) > 1e-5 else 0.0
        X_R0, Y_R0 = vec.R_line[0, 0], vec.R_line[0, 1]
        
        m_axis = (m_L + m_R) / 2.0
        m_chord_ortho = -m_axis  # Идеальный перпендикуляр для фильтрации
        
        def intersect_parabola_with_lateral(poly, is_left=True):
            # Быстрая итеративная аппроксимация точки пересечения параболы и боковой прямой
            m_lat = m_L if is_left else m_R
            X_lat0 = X_L0 if is_left else X_R0
            Y_lat0 = Y_L0 if is_left else Y_R0
            
            x_est = X_lat0
            for _ in range(3):
                y_est = np.polyval(poly, x_est)
                x_est = X_lat0 + m_lat * (y_est - Y_lat0)
            return x_est, np.polyval(poly, x_est)

        valid_curves = []
        guides = []
        
        def is_complex_curvature(curve_pts):
            # Если кривая является горизонтальным сечением цилиндра, она должна быть идеальной параболой.
            # Если это фигурный вырез (герб), она будет отклоняться от параболы.
            try:
                p = np.polyfit(curve_pts[:, 0], curve_pts[:, 1], 2)
                preds = np.polyval(p, curve_pts[:, 0])
                max_err = np.max(np.abs(preds - curve_pts[:, 1]))
                return max_err > 3.0
            except:
                return False

        def add_curve_if_valid(curve_pts, is_text):
            # curve_pts shape (N, 2)
            actual_chord_m = (curve_pts[-1, 1] - curve_pts[0, 1]) / (curve_pts[-1, 0] - curve_pts[0, 0] + 1e-5)
            angle_diff = np.degrees(np.arctan(abs((actual_chord_m - m_chord_ortho) / (1 + actual_chord_m * m_chord_ortho))))
            
            if angle_diff <= 15.0 and not is_complex_curvature(curve_pts):
                valid_curves.append(curve_pts)
                guides.append({"v": np.mean(curve_pts[:, 1]), "curve": curve_pts, "is_text": is_text})
                
        def resample_curve(curve_pts, num_pts):
            if len(curve_pts) == num_pts: return curve_pts
            u_old = np.linspace(0.0, 1.0, len(curve_pts))
            u_new = np.linspace(0.0, 1.0, num_pts)
            x_new = np.interp(u_new, u_old, curve_pts[:, 0])
            y_new = np.interp(u_new, u_old, curve_pts[:, 1])
            return np.column_stack((x_new, y_new))

        # T_curve и B_curve - ДОБАВЛЯЕМ БЕЗ УСЛОВИЙ, это физические границы (не должны отбрасываться фильтрами)
        T_resampled = resample_curve(vec.T_curve, grid_cols)
        B_resampled = resample_curve(vec.B_curve, grid_cols)
        
        valid_curves.append(T_resampled)
        guides.append({"v": np.mean(T_resampled[:, 1]), "curve": T_resampled, "is_text": False})
        
        valid_curves.append(B_resampled)
        guides.append({"v": np.mean(B_resampled[:, 1]), "curve": B_resampled, "is_text": False})
        
        # Текстовые параболы
        if hasattr(vec, 'text_parabolas') and vec.text_parabolas:
            for item in vec.text_parabolas:
                if isinstance(item, tuple) and len(item) == 2:
                    poly, pts = item
                else:
                    poly = item
                    pts = None
                    
                x_L, y_L = intersect_parabola_with_lateral(poly, is_left=True)
                x_R, y_R = intersect_parabola_with_lateral(poly, is_left=False)
                
                # Если парабола вырождена или перевернута, пропускаем
                if x_R <= x_L: continue
                
                x_base = np.linspace(x_L, x_R, grid_cols)
                ys = np.polyval(poly, x_base)
                curve_pts = np.column_stack((x_base, ys))
                
                actual_chord_m = (curve_pts[-1, 1] - curve_pts[0, 1]) / (curve_pts[-1, 0] - curve_pts[0, 0] + 1e-5)
                angle_diff = np.degrees(np.arctan(abs((actual_chord_m - m_chord_ortho) / (1 + actual_chord_m * m_chord_ortho))))
                
                if angle_diff <= 18.0 and not is_complex_curvature(curve_pts):
                    valid_curves.append(curve_pts)
                    guides.append({"v": np.mean(curve_pts[:, 1]), "curve": curve_pts, "is_text": True, "pts": pts})
                
        # Консенсус-фильтр углов: если >=3 кривых параллельны (в пределах 4 град), 
        # а остальные сильно отклоняются - удаляем выбросы (но защищаем границы маски)
        if len(valid_curves) >= 4:
            angles = [np.degrees(np.arctan((c[-1, 1] - c[0, 1]) / (c[-1, 0] - c[0, 0] + 1e-5))) for c in valid_curves]
            
            best_cluster = []
            for i in range(len(angles)):
                cluster = [j for j in range(len(angles)) if abs(angles[j] - angles[i]) <= 4.0]
                if len(cluster) > len(best_cluster):
                    best_cluster = cluster
                    
            if len(best_cluster) >= 3:
                median_angle = np.median([angles[j] for j in best_cluster])
                filtered_valid = []
                filtered_guides = []
                for idx, c in enumerate(valid_curves):
                    is_text = guides[idx].get("is_text", False)
                    # Фильтруем только текстовые параболы, физические границы T/B остаются всегда
                    if not is_text or abs(angles[idx] - median_angle) <= 4.0:
                        filtered_valid.append(c)
                        filtered_guides.append(guides[idx])
                valid_curves = filtered_valid
                guides = filtered_guides

        # Сортируем валидные кривые сверху вниз
        valid_curves.sort(key=lambda c: np.mean(c[:, 1]))
        
        # Если нет валидных кривых - создаем фейковые перпендикулярные
        if len(valid_curves) == 0:
            def fake_curve(Y_val):
                y_L = Y_val
                x_L = X_L0 + m_L * (y_L - Y_L0)
                y_R = Y_val
                x_R = X_R0 + m_R * (y_R - Y_R0)
                x_base = np.linspace(x_L, x_R, grid_cols)
                ys = np.linspace(y_L, y_R, grid_cols)
                return np.column_stack((x_base, ys))
            valid_curves = [fake_curve(vec.bbox[1]), fake_curve(vec.bbox[1] + vec.bbox[3])]
            
        if len(valid_curves) == 1:
            c0 = valid_curves[0]
            # Сдвигаем на 100 пикселей вниз по RANSAC-направляющим
            c1 = np.zeros_like(c0)
            c1[:, 0] = c0[:, 0] + (m_L * 100.0 * (1 - u_norm_prof) + m_R * 100.0 * u_norm_prof)
            c1[:, 1] = c0[:, 1] + 100.0
            valid_curves.append(c1)

        # 3. Генерация сетки (Интерполяция/Экстраполяция между штрихами)
        target_y_min = max(0, vec.bbox[1] - 20)
        target_y_max = min(h_c - 1, vec.bbox[1] + vec.bbox[3] + 20)
        
        grid_rows_ext = int((target_y_max - target_y_min) / 4.0)
        grid_rows_ext = max(grid_rows_ext, 10)
        y_g = np.linspace(target_y_min, target_y_max, grid_rows_ext)
        
        u_grid = np.zeros((grid_rows_ext, grid_cols), dtype=np.float32)
        v_grid = np.zeros((grid_rows_ext, grid_cols), dtype=np.float32)
        
        means = [np.mean(c[:, 1]) for c in valid_curves]
        
        for r in range(grid_rows_ext):
            y_target = y_g[r]
            
            # Находим нужный сегмент
            idx = 0
            while idx < len(means) - 2 and y_target > means[idx + 1]:
                idx += 1
                
            c_top = valid_curves[idx]
            c_bot = valid_curves[idx + 1]
            y_top = means[idx]
            y_bot = means[idx + 1]
            
            t = (y_target - y_top) / (y_bot - y_top + 1e-5)
            
            # Линейная интерполяция/экстраполяция координат
            curve_interp = (1.0 - t) * c_top + t * c_bot
            
            u_grid[r, :] = np.clip(curve_interp[:, 0], 0, w_c - 1)
            v_grid[r, :] = np.clip(curve_interp[:, 1], 0, h_c - 1)
            
        # Stage 3: Regularized Mesh generation
        t_s3_0 = time.perf_counter()
        arc_T = np.sum(np.hypot(np.diff(u_grid[0, :]), np.diff(v_grid[0, :])))
        arc_B = np.sum(np.hypot(np.diff(u_grid[-1, :]), np.diff(v_grid[-1, :])))
        dst_w = max(int(round(max(arc_T, arc_B))), 100)
        dst_h = max(int(round(target_y_max - target_y_min)), 100)
        map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        stage3_ms = (time.perf_counter() - t_s3_0) * 1000.0

        # Stage 4: Surface Remapping / Dewarping
        t_s4_0 = time.perf_counter()
        dewarped = cv2.remap(rot_img, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
        stage4_ms = (time.perf_counter() - t_s4_0) * 1000.0
        
        # Diagnostic visual features
        vis_features = rot_img.copy()
        
        cv2.polylines(vis_features, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        
        # Отрисовка точек контура, по которым строились дуги и прямые (для отладки)
        for pts, color in [
            (vec.raw_T, (0, 255, 255)), # Желтый для верха
            (vec.raw_B, (255, 255, 0)), # Голубой для низа
            (vec.raw_L, (255, 0, 255)), # Пурпурный для левой
            (vec.raw_R, (255, 0, 255))  # Пурпурный для правой
        ]:
            if pts is not None:
                for pt in pts:
                    cv2.circle(vis_features, (int(pt[0]), int(pt[1])), 2, color, -1, cv2.LINE_AA)

        # Отрисовка всех валидных штрихов
        for g in guides:
            color = (0, 0, 255) if g.get("is_text") else (0, 255, 0)
            cv2.polylines(vis_features, [g["curve"].astype(np.int32)], False, color, 2, cv2.LINE_AA)
            if "pts" in g and g["pts"] is not None:
                for pt in g["pts"]:
                    cv2.circle(vis_features, (int(pt[0]), int(pt[1])), 6, (255, 0, 255), -1, cv2.LINE_AA)
                    cv2.circle(vis_features, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), 1, cv2.LINE_AA)
            
        for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:
            cv2.circle(vis_features, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.circle(vis_features, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), 2, cv2.LINE_AA)
            
        # Diagnostic 3D mesh
        vis_mesh = rot_img.copy()
        for r in range(grid_rows_ext):
            pts_r = np.column_stack((u_grid[r, :], v_grid[r, :])).astype(np.int32)
            cv2.polylines(vis_mesh, [pts_r], False, (0, 220, 255), 1, cv2.LINE_AA)
        for c in range(grid_cols):
            pts_c = np.column_stack((u_grid[:, c], v_grid[:, c])).astype(np.int32)
            cv2.polylines(vis_mesh, [pts_c], False, (0, 180, 255), 1, cv2.LINE_AA)
            
        # 5. OCR on Dewarped Scan (Stage 5)
        t_ocr_dew_0 = time.perf_counter()
        ocr_dew = self.stage5.process(dewarped)
        t_ocr_dew_ms = (time.perf_counter() - t_ocr_dew_0) * 1000.0
        
        return {
            "dewarped": dewarped,
            "rot_crop": rot_img,
            "rot_mask": rot_mask,
            "vis_features": vis_features,
            "vis_mesh": vis_mesh,
            "vector_mask": vec,
            "ocr_raw": ocr_raw,
            "ocr_dew": ocr_dew,
            "bisector_angle": theta,
            "tier_timings": {
                "stage2_ms": round(stage2_ms, 1),
                "stage3_ms": round(stage3_ms, 1),
                "stage4_ms": round(stage4_ms, 1),
                "ocr_raw_ms": round(t_ocr_raw_ms, 1),
                "ocr_dew_ms": round(t_ocr_dew_ms, 1)
            }
        }

    @staticmethod
    def check_has_micro_fonts(img_bgr: np.ndarray) -> bool:
        """
        Быстрый (10-15 мс) детектор наличия мелких шрифтов (6-10 pt) на фото.
        Если мелких шрифтов нет (крупный шрифт/чистая этикетка), возвращает False,
        что позволяет безопасно масштабировать кадр до 1800 px.
        """
        h, w = img_bgr.shape[:2]
        if max(h, w) <= 1800:
            return False
        scale = 0.5
        small = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        grad_x = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
        thresh = (grad_x > 35).astype(np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (4, 1))
        connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        _, _, stats, _ = cv2.connectedComponentsWithStats(connected)
        h_comps = stats[1:, cv2.CC_STAT_HEIGHT]
        w_comps = stats[1:, cv2.CC_STAT_WIDTH]
        micro_mask = (h_comps >= 4) & (h_comps <= 14) & (w_comps >= 6) & (w_comps <= 250)
        count_micro = int(np.sum(micro_mask))
        return count_micro >= 60

    def process_image(self, 
                      img_bgr: np.ndarray, 
                      reference_bgr: np.ndarray = None,
                      save_dir: str = None) -> dict:
        """
        Executes single dominant label segmentation and dual verification dewarping.
        """
        start_total = time.perf_counter()
        timings = {}
        h_orig, w_orig = img_bgr.shape[:2]
        
        proc_img = img_bgr
        if h_orig > 1920 and w_orig > 1080:
            scale_in = max(1920.0 / float(h_orig), 1080.0 / float(w_orig))
            if scale_in < 1.0:
                proc_img = cv2.resize(img_bgr, (int(round(w_orig * scale_in)), int(round(h_orig * scale_in))), interpolation=cv2.INTER_AREA)

        # 1. Localization & Cropping of Single Largest Label Mask
        t0 = time.perf_counter()
        cropped_bgr, cropped_mask, bbox_info = self.stage1.segment_bottle_and_label(proc_img)
        cropped_mask = self.stage1._keep_largest_component(cropped_mask)
        timings["stage1_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

        # 2. Dewarping & Dual OCR Verification
        t0 = time.perf_counter()
        res = self._dewarp_single_tier(cropped_bgr, cropped_mask)
        
        dewarped_display = res["dewarped"]
        annotated_dew_display = res["ocr_dew"]["annotated_bgr"]
        annotated_raw_display = res["ocr_raw"]["annotated_bgr"]
        crop_display = res["rot_crop"]
        mask_display = res["rot_mask"]
        features_display = res["vis_features"]
        mesh_display = res["vis_mesh"]
        
        raw_text, raw_corrs = self.lexicon.correct_text(res["ocr_raw"]["full_text"])
        raw_tokens = []
        raw_words = 0
        for t in res["ocr_raw"]["text_blocks"]:
            t_cor, _ = self.lexicon.correct_text(t["text"])
            if t_cor.strip():
                t_copy = dict(t)
                t_copy["text"] = t_cor
                raw_tokens.append(t_copy)
                if not t.get("is_stopword"):
                    raw_words += len(t_cor.split())
        
        dew_text, dew_corrs = self.lexicon.correct_text(res["ocr_dew"]["full_text"])
        dew_tokens = []
        dew_words = 0
        for t in res["ocr_dew"]["text_blocks"]:
            t_cor, _ = self.lexicon.correct_text(t["text"])
            if t_cor.strip():
                t_copy = dict(t)
                t_copy["text"] = t_cor
                dew_tokens.append(t_copy)
                if not t.get("is_stopword"):
                    dew_words += len(t_cor.split())
        
        all_corrections = dew_corrs if dew_words >= raw_words else raw_corrs
        all_codes = res["ocr_dew"].get("codes", [])
        
        tier_t = res.get("tier_timings", {})
        timings["stage2_ms"] = tier_t.get("stage2_ms", 0.0)
        timings["stage3_ms"] = tier_t.get("stage3_ms", 0.0)
        timings["stage4_ms"] = tier_t.get("stage4_ms", 0.0)
        timings["stage5_ms"] = round(tier_t.get("ocr_dew_ms", 0.0) + tier_t.get("ocr_raw_ms", 0.0), 1)
        
        vec = res["vector_mask"]
        theta_bisector = res["bisector_angle"]

        # Decision Logic: VLM mode directly takes the high-precision dewarped scan; classic uses word gain
        if self.ocr_engine == "vlm":
            gain = dew_words
            selected_source = "dewarped"
            selected_text = dew_text
            selected_tokens = dew_tokens
            selected_annotated = annotated_dew_display
            decision_status = "VLM (Qwen2-VL 100% GPU прямой скан)"

            # Если на выпрямленном скане не распознались слова (узкая/деформированная этикетка),
            # опрашиваем Qwen2-VL по исходному кадру бутылки
            if dew_words <= 1:
                try:
                    from .stage5_vlm import WineVLMDecoder
                    vlm_inst = WineVLMDecoder.get_instance()
                    vlm_raw = vlm_inst.read_label(img_bgr)
                    raw_vlm_text = vlm_raw.get("text", "").strip().replace("\n", " ")
                    raw_vlm_cor, _ = self.lexicon.correct_text(raw_vlm_text)
                    if len(raw_vlm_cor.split()) > dew_words:
                        selected_text = raw_vlm_cor
                        selected_source = "raw_full"
                        decision_status = f"VLM (Qwen2-VL полный кадр: {len(raw_vlm_cor.split())} сл)"
                except Exception as e_vlm:
                    pass
        else:
            gain = dew_words - raw_words
            if dew_words >= raw_words:
                selected_source = "dewarped"
                selected_text = dew_text
                selected_tokens = dew_tokens
                selected_annotated = annotated_dew_display
                decision_status = f"+{gain} сл (прирост - выбран выпрямленный скан)" if gain > 0 else "0 (точное сохранение - выбран выпрямленный скан)"
            else:
                selected_source = "raw"
                selected_text = raw_text
                selected_tokens = raw_tokens
                selected_annotated = annotated_raw_display
                decision_status = f"{gain} сл (неудачная трансформация - выбран исходный захват)"

        # --- MICROSCOPE: Second-pass OCR (only needed for classic OCR to catch small text) ---
        if self.ocr_engine != "vlm":
            try:
                micro_source = dewarped_display if selected_source == "dewarped" else crop_display
                mh, mw = micro_source.shape[:2]
                bottom_crop = micro_source[int(mh * 0.65):, :]
                if bottom_crop.size > 0:
                    bh, bw = bottom_crop.shape[:2]
                    if bh > 10 and bw > 10:
                        bottom_2x = cv2.resize(bottom_crop, (bw * 2, bh * 2), interpolation=cv2.INTER_CUBIC)
                        t_micro_0 = time.perf_counter()
                        micro_ocr = self.stage5.process(bottom_2x)
                        t_micro_ms = (time.perf_counter() - t_micro_0) * 1000.0
                        timings["stage5_ms"] = round(timings.get("stage5_ms", 0.0) + t_micro_ms, 1)
                        micro_text_raw = micro_ocr.get("full_text", "")
                        if micro_text_raw.strip():
                            micro_text, _ = self.lexicon.correct_text(micro_text_raw)
                            # Only append genuinely new words not already in selected_text
                            existing_words = set(selected_text.upper().split())
                            new_words = [w for w in micro_text.split() if w.upper() not in existing_words and len(w) > 1]
                            if new_words:
                                selected_text = selected_text + " " + " ".join(new_words)
                                print(f"[Microscope] Found new text in bottom zone: '{' '.join(new_words)}'")
            except Exception as e:
                print(f"[Microscope] Error: {e}")

        # --- MULTI-LABEL VERTICAL STITCHING & OCR: Process and dewarp additional labels ---
        try:
            bottle_labels = bbox_info.get("bottle_labels", [])
            # Сортируем все наклейки строго по вертикали (сверху вниз по Y-координате)
            sorted_labels = sorted(bottle_labels, key=lambda l: l["box"][1])

            # Early Exit: если первичная наклейка уже содержит сорт винограда И (цвет или сладость или спец-линейку),
            # опрос второстепенных наклеек (кольереток, медалей) не требуется — экономим до 15 секунд!
            from .wine_thesaurus import extract_grape_concepts, COLOR_ONTOLOGY, SWEETNESS_ONTOLOGY, SPECIAL_WINE_TERMS
            sel_upper = selected_text.upper()
            has_p_grape = bool(extract_grape_concepts(sel_upper))
            has_p_color = any(any(w in sel_upper for w in words) for words in COLOR_ONTOLOGY.values())
            has_p_sweet = any(any(w in sel_upper for w in words) for words in SWEETNESS_ONTOLOGY.values())
            has_p_special = any(any(w in sel_upper for w in words) for words in SPECIAL_WINE_TERMS.values())
            
            skip_secondary = (has_p_grape and (has_p_color or has_p_sweet or has_p_special))

            if len(sorted_labels) > 1 and not skip_secondary:
                dewarped_segments = []
                # Находим соответствие или выпрямляем каждую наклейку
                for l_idx, lbl in enumerate(sorted_labels):
                    sbx1, sby1, sbx2, sby2 = lbl["box"]
                    # Если это первичная и уже выпрямлена - используем её результат
                    if lbl.get("is_primary", False) and dewarped_display is not None and dewarped_display.size > 0:
                        dewarped_segments.append(dewarped_display)
                    else:
                        h_p, w_p = proc_img.shape[:2]
                        spad = 12
                        sx0, sy0 = max(0, sbx1 - spad), max(0, sby1 - spad)
                        sx1, sy1 = min(w_p, sbx2 + spad), min(h_p, sby2 + spad)
                        sec_crop_bgr = proc_img[sy0:sy1, sx0:sx1]

                        sec_mask = lbl.get("mask")
                        if sec_mask is not None:
                            sec_crop_mask = sec_mask[sy0:sy1, sx0:sx1]
                        else:
                            sec_crop_mask = np.ones((sy1 - sy0, sx1 - sx0), dtype=np.uint8) * 255

                        try:
                            sec_res = self._dewarp_single_tier(sec_crop_bgr, sec_crop_mask)
                            sec_t = sec_res.get("tier_timings", {})
                            timings["stage2_ms"] = round(timings.get("stage2_ms", 0.0) + sec_t.get("stage2_ms", 0.0), 1)
                            timings["stage3_ms"] = round(timings.get("stage3_ms", 0.0) + sec_t.get("stage3_ms", 0.0), 1)
                            timings["stage4_ms"] = round(timings.get("stage4_ms", 0.0) + sec_t.get("stage4_ms", 0.0), 1)
                            timings["stage5_ms"] = round(timings.get("stage5_ms", 0.0) + sec_t.get("ocr_dew_ms", 0.0) + sec_t.get("ocr_raw_ms", 0.0), 1)
                            sec_dew = sec_res.get("dewarped")
                            if sec_dew is not None and sec_dew.size > 0:
                                dewarped_segments.append(sec_dew)
                                # Дополняем распознанный текст со второй этикетки
                                sec_txt_raw = sec_res["ocr_dew"]["full_text"]
                                if sec_txt_raw.strip():
                                    sec_txt_cor, _ = self.lexicon.correct_text(sec_txt_raw)
                                    existing_words = set(selected_text.upper().split())
                                    new_sec_words = [w for w in sec_txt_cor.split() if w.upper() not in existing_words and len(w) > 1]
                                    if new_sec_words:
                                        selected_text = selected_text + " " + " ".join(new_sec_words)
                        except Exception as e_sec:
                            print(f"[MultiLabel] Dewarping segment #{l_idx+1} warning: {e_sec}")
                            dewarped_segments.append(sec_crop_bgr)

                # Если успешно получено несколько сегментов, сшиваем по вертикали
                if len(dewarped_segments) > 1:
                    max_w = max(seg.shape[1] for seg in dewarped_segments)
                    aligned_segments = []
                    for seg in dewarped_segments:
                        sh, sw = seg.shape[:2]
                        if sw != max_w:
                            seg = cv2.resize(seg, (max_w, int(sh * (max_w / float(sw)))))
                        aligned_segments.append(seg)

                    # Разделитель между этикетками (20 пикселей)
                    gap = np.zeros((20, max_w, 3), dtype=np.uint8)
                    stacked_result = aligned_segments[0]
                    for seg in aligned_segments[1:]:
                        stacked_result = np.vstack([stacked_result, gap, seg])

                    dewarped_display = stacked_result
                    print(f"[MultiLabel] Successfully stitched {len(dewarped_segments)} labels vertically. New canvas shape: {dewarped_display.shape}")

        except Exception as e:
            print(f"[MultiLabel] Vertical stitching error: {e}")

        total_ms = round((time.perf_counter() - start_total) * 1000.0, 1)
        timings["total_ms"] = total_ms

        quality_metrics = {}
        if reference_bgr is not None:
            quality_metrics = compute_image_metrics(dewarped_display, reference_bgr)

        return {
            "success": True,
            "timings": timings,
            "metrics": quality_metrics,
            "selected_source": selected_source,
            "decision_status": decision_status,
            "text_blocks": selected_tokens,
            "full_text": selected_text,
            "num_words": len(selected_tokens),
            "lexicon_corrections": all_corrections,
            "barcodes": all_codes,
            "comparison": {
                "raw": {
                    "num_words": raw_words,
                    "full_text": raw_text,
                    "text_blocks": raw_tokens,
                    "image": self.img_to_base64(crop_display),
                    "annotated": self.img_to_base64(annotated_raw_display)
                },
                "dewarped": {
                    "num_words": dew_words,
                    "full_text": dew_text,
                    "text_blocks": dew_tokens,
                    "image": self.img_to_base64(dewarped_display),
                    "annotated": self.img_to_base64(annotated_dew_display)
                },
                "gain": gain,
                "status": decision_status,
                "recommended": selected_source
            },
            "opt_params": {
                "P_TL": vec.P_TL.tolist(), "P_TR": vec.P_TR.tolist(),
                "P_BL": vec.P_BL.tolist(), "P_BR": vec.P_BR.tolist(),
                "bisector_angle": round(theta_bisector, 2)
            },
            "cam_info": {"tilt_angle": round(theta_bisector, 2), "status": "Verticalized 90°"},
            "artifacts": {
                "original": self.img_to_base64(img_bgr),
                "cropped": self.img_to_base64(crop_display),
                "mask": self.img_to_base64(mask_display),
                "retinex": self.img_to_base64(crop_display),
                "binarized": self.img_to_base64(mask_display),
                "features": self.img_to_base64(features_display),
                "mesh": self.img_to_base64(mesh_display),
                "dewarped": self.img_to_base64(dewarped_display),
                "annotated": self.img_to_base64(selected_annotated)
            }
        }
