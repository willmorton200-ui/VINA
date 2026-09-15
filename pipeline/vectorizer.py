"""
Vectorizer Module: Direct Perimeter & Monotone Semi-Ellipsoid Vectorization of Binary Mask
- Step 1: Input mask refined via Solution 3 (Photometric Paper Gate).
- Step 2: Lateral tangent lines (side generators) intersect top and bottom horizontal curves to define 4 exact corner vertices (P_TL, P_TR, P_BL, P_BR).
- Step 3: Connect corner vertices with true semi-ellipses fitted to the source mask profiles using the Monotone Single-Curvature Rule with Edge Priority (no S-curves, no parasitic middle humps).
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Optional
from enum import Enum

class LabelShape(Enum):
    CYLINDER = "cylinder"
    RECTANGLE = "rectangle"

@dataclass
class VectorMask:
    shape_type: LabelShape
    bbox: Tuple[int, int, int, int]
    P_TL: np.ndarray
    P_TR: np.ndarray
    P_BL: np.ndarray
    P_BR: np.ndarray
    T_curve: np.ndarray
    B_curve: np.ndarray
    L_line: np.ndarray
    R_line: np.ndarray
    polygon: np.ndarray
    left_line: np.ndarray = None
    right_line: np.ndarray = None
    top_curve: np.ndarray = None
    bottom_curve: np.ndarray = None

class MaskVectorizer:
    def __init__(self):
        pass

    def _fit_monotone_semi_ellipse(
        self,
        raw_ys: np.ndarray,
        P_left: np.ndarray,
        P_right: np.ndarray,
        preferred_direction: str = "smile",
        forced_apex_y: Optional[float] = None,
        N_pts: int = 60
    ) -> np.ndarray:
        """
        Fits a canonical semi-ellipse connecting P_left and P_right:
        - Strict monotone single curvature (no double curvature, no central humps).
        - Edge-priority weighting (u <= 0.30 or u >= 0.70).
        """
        N = len(raw_ys)
        u_norm = np.linspace(0.0, 1.0, N)
        y_corner_avg = (P_left[1] + P_right[1]) / 2.0
        
        if forced_apex_y is not None:
            # Directly use the measured apex height relative to corners
            delta_final = forced_apex_y - y_corner_avg
        else:
            # 1. Edge-priority weights: w=4 on corners, w=1 in center
            edge_weights = 1.0 + 3.0 * (2.0 * u_norm - 1.0) ** 2
            tilt_linear = (1.0 - u_norm) * P_left[1] + u_norm * P_right[1]
            raw_delta = raw_ys - tilt_linear
            sin_vals = np.sin(np.pi * u_norm)
            
            # 2. Fit delta using ONLY reliable edge sections (u <= 0.30 or u >= 0.70)
            edge_mask = (u_norm <= 0.30) | (u_norm >= 0.70)
            num = np.sum(edge_weights[edge_mask] * raw_delta[edge_mask] * sin_vals[edge_mask])
            den = np.sum(edge_weights[edge_mask] * (sin_vals[edge_mask] ** 2))
            delta_edge = num / max(den, 1e-6)
            
            if preferred_direction == "smile":
                delta_final = max(delta_edge, 2.0)
            elif preferred_direction == "frown":
                delta_final = min(delta_edge, -2.0)
            else:
                delta_final = delta_edge
                
        # Clamp sagitta to realistic physical bottle bounds (max 15% of label chord width)
        a = max(abs(P_right[0] - P_left[0]) / 2.0, 1.0)
        max_delta = 0.15 * (2.0 * a)
        delta_final = float(np.clip(delta_final, -max_delta, max_delta))
        
        # 3. Construct canonical blended curve (smooth blend between semi-ellipse and circular/parabolic arc)
        theta = np.linspace(0.0, np.pi, N_pts)
        u_norm = theta / np.pi
        x0 = (P_left[0] + P_right[0]) / 2.0
        a = max(abs(P_right[0] - P_left[0]) / 2.0, 1.0)
        
        ell_x = x0 - a * np.cos(theta)
        tilt = (1.0 - u_norm) * P_left[1] + u_norm * P_right[1] - y_corner_avg
        
        # Profile: blend 50% semi-ellipse sin(theta) and 50% parabolic arc 4*u*(1-u)
        profile_ellipse = np.sin(theta)
        profile_arc = 4.0 * u_norm * (1.0 - u_norm)
        profile_blended = 0.5 * profile_ellipse + 0.5 * profile_arc
        
        ell_y = y_corner_avg + delta_final * profile_blended + tilt
        ell_y[0] = P_left[1]
        ell_y[-1] = P_right[1]
        
        return np.column_stack((ell_x, ell_y))

    def _smooth_horizontal_guide(
        self,
        raw_curve: np.ndarray,
        P_left: np.ndarray,
        P_right: np.ndarray,
        N_pts: int = 60
    ) -> np.ndarray:
        """
        Сглаживает верхнюю или нижнюю горизонтальную направляющую, устраняя
        высокочастотную рябь и ступенчатость пикселей маски, сохраняя глобальную физическую дугу цилиндра.
        Использует ортогональный гармонический базис (Fourier Sine Series) с
        жестким закреплением граничных угловых точек P_left и P_right.
        """
        N = len(raw_curve)
        u = np.linspace(0.0, 1.0, N)
        
        # 1. Линейная хорда между углами
        chord_x = (1.0 - u) * P_left[0] + u * P_right[0]
        chord_y = (1.0 - u) * P_left[1] + u * P_right[1]
        
        # 2. Отклонения от хорды
        delta_x = raw_curve[:, 0] - chord_x
        delta_y = raw_curve[:, 1] - chord_y
        
        # 3. Ортогональный гармонический базис Фурье (sin(k*pi*u)), равный строго 0 на границах u=0 и u=1
        S1 = np.sin(np.pi * u)
        S2 = np.sin(2.0 * np.pi * u)
        S3 = np.sin(3.0 * np.pi * u)
        A = np.column_stack((S1, S2, S3))
        
        c_y, _, _, _ = np.linalg.lstsq(A, delta_y, rcond=None)
        c_x, _, _, _ = np.linalg.lstsq(A, delta_x, rcond=None)
        
        y_smooth = chord_y + A @ c_y
        x_smooth = chord_x + A @ c_x
        
        # Жесткое закрепление угловых точек (0 пикселей отклонения)
        y_smooth[0], y_smooth[-1] = P_left[1], P_right[1]
        x_smooth[0], x_smooth[-1] = P_left[0], P_right[0]
        
        return np.column_stack((x_smooth, y_smooth))

    def _fit_straight_lateral_guide(
        self,
        raw_segment: np.ndarray,
        P_top: np.ndarray,
        P_bot: np.ndarray,
        max_dev_px: float = 6.0,
        N_pts: int = 60
    ) -> np.ndarray:
        """
        Проверяет боковую образующую на ровность при углах ~180° (прямолинейность),
        игнорирует резкие пороги/ступени посередине и строит гладкую образующую.
        """
        M = len(raw_segment)
        if M < 5:
            v_vals = np.linspace(0.0, 1.0, N_pts)
            return (1.0 - v_vals[:, None]) * P_top + v_vals[:, None] * P_bot

        ys = raw_segment[:, 1]
        xs = raw_segment[:, 0]
        
        # 1. Проверка локальных углов (ровность при угле ~ 180 град)
        k = max(2, min(5, M // 8))
        is_flat = np.ones(M, dtype=bool)
        for i in range(k, M - k):
            v1 = raw_segment[i] - raw_segment[i - k]
            v2 = raw_segment[i + k] - raw_segment[i]
            n1 = np.hypot(v1[0], v1[1])
            n2 = np.hypot(v2[0], v2[1])
            if n1 > 1e-3 and n2 > 1e-3:
                cos_a = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
                turn_deg = np.degrees(np.arccos(cos_a))
                if turn_deg > 25.0:  # Резкий локальный порог / ступенька
                    is_flat[i] = False

        flat_ys = ys[is_flat]
        flat_xs = xs[is_flat]

        if len(flat_ys) >= 6:
            poly = np.polyfit(flat_ys, flat_xs, deg=1)
            resids = np.abs(flat_xs - np.polyval(poly, flat_ys))
            inliers = resids <= max_dev_px
            if np.count_nonzero(inliers) >= 4:
                poly_refined = np.polyfit(flat_ys[inliers], flat_xs[inliers], deg=1)
            else:
                poly_refined = poly
        else:
            dy = P_bot[1] - P_top[1]
            dx = P_bot[0] - P_top[0]
            m = dx / max(abs(dy), 1e-4)
            c = P_top[0] - m * P_top[1]
            poly_refined = np.array([m, c])

        v_vals = np.linspace(0.0, 1.0, N_pts)
        y_gen = (1.0 - v_vals) * P_top[1] + v_vals * P_bot[1]
        x_gen = np.polyval(poly_refined, y_gen)
        x_gen[0] = P_top[0]
        x_gen[-1] = P_bot[0]
        return np.column_stack((x_gen, y_gen))

    def vectorize(self, mask: np.ndarray) -> VectorMask:
        if len(mask.shape) == 3:
            if mask.shape[2] == 3:
                mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            else:
                mask = mask[:, :, 0]

        h, w = mask.shape[:2]
        
        # 1. Retain largest component
        binary = np.uint8(mask > 127)
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        if num_labels > 2:
            largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            clean_mask = np.zeros((h, w), dtype=np.uint8)
            clean_mask[labels == largest_label] = 255
            mask = clean_mask

        # Morphological closing
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        y_indices, x_indices = np.where(mask_closed > 127)
        if len(y_indices) == 0:
            P_TL = np.array([0.0, 0.0])
            P_TR = np.array([w - 1.0, 0.0])
            P_BL = np.array([0.0, h - 1.0])
            P_BR = np.array([w - 1.0, h - 1.0])
            return VectorMask(
                shape_type=LabelShape.RECTANGLE,
                bbox=(0, 0, w, h),
                P_TL=P_TL, P_TR=P_TR, P_BL=P_BL, P_BR=P_BR,
                T_curve=np.array([P_TL, P_TR]),
                B_curve=np.array([P_BL, P_BR]),
                L_line=np.array([P_TL, P_BL]),
                R_line=np.array([P_TR, P_BR]),
                polygon=np.array([P_TL, P_TR, P_BR, P_BL], dtype=np.int32),
                left_line=np.array([0.0, 0.0]),
                right_line=np.array([0.0, float(w - 1)]),
                top_curve=np.array([P_TL, P_TR]),
                bottom_curve=np.array([P_BL, P_BR])
            )

        x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))
        y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
        H_mask = y_max - y_min

        # 2. Extract row-by-row left and right points along the mask
        valid_ys = np.unique(y_indices)
        left_pts = []
        right_pts = []
        for y in valid_ys:
            col_xs = np.where(mask_closed[y, :] > 127)[0]
            if len(col_xs) > 0:
                left_pts.append((float(col_xs[0]), float(y)))
                right_pts.append((float(col_xs[-1]), float(y)))

        left_pts = np.array(left_pts)
        right_pts = np.array(right_pts)

        # 4. Fit Lateral Tangent Lines (Касательные образующие цилиндра x = m*y + c)
        # Use middle region of mask height (25% to 75%) for stable regression
        mid_mask_L = (left_pts[:, 1] >= y_min + 0.25 * H_mask) & (left_pts[:, 1] <= y_min + 0.75 * H_mask)
        mid_mask_R = (right_pts[:, 1] >= y_min + 0.25 * H_mask) & (right_pts[:, 1] <= y_min + 0.75 * H_mask)

        if np.count_nonzero(mid_mask_L) >= 8:
            poly_L = np.polyfit(left_pts[mid_mask_L, 1], left_pts[mid_mask_L, 0], deg=1)
        else:
            poly_L = np.array([0.0, float(x_min)])

        if np.count_nonzero(mid_mask_R) >= 8:
            poly_R = np.polyfit(right_pts[mid_mask_R, 1], right_pts[mid_mask_R, 0], deg=1)
        else:
            poly_R = np.array([0.0, float(x_max)])

        # 5. Extract continuous external contour
        contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if not contours:
            P_TL = np.array([float(x_min), float(y_min)])
            P_TR = np.array([float(x_max), float(y_min)])
            P_BL = np.array([float(x_min), float(y_max)])
            P_BR = np.array([float(x_max), float(y_max)])
            return VectorMask(
                shape_type=LabelShape.CYLINDER,
                bbox=(x_min, y_min, x_max - x_min, y_max - y_min),
                P_TL=P_TL, P_TR=P_TR, P_BL=P_BL, P_BR=P_BR,
                T_curve=np.array([P_TL, P_TR]),
                B_curve=np.array([P_BL, P_BR]),
                L_line=np.array([P_TL, P_BL]),
                R_line=np.array([P_TR, P_BR]),
                polygon=np.array([P_TL, P_TR, P_BR, P_BL], dtype=np.int32)
            )

        cnt = max(contours, key=cv2.contourArea)
        pts_cnt = cnt.squeeze(1)
        N_cnt = len(pts_cnt)

        # 6. АВТОМАТИЧЕСКОЕ УНИВЕРСАЛЬНОЕ ПРАВИЛО: МИНИМАЛЬНЫЙ ВНУТРЕННИЙ УГОЛ КОНТУРА
        # Вычисляем непрерывное распределение внутренних углов alpha(i) по всему контуру
        # Точки P_TL, P_TR, P_BL, P_BR — это СТРОГИЙ ГЛОБАЛЬНЫЙ МИНИМУМ внутреннего угла alpha в каждом из 4 квадрантов
        k_step = max(5, int(N_cnt * 0.015))
        internal_angles = np.zeros(N_cnt)
        for i in range(N_cnt):
            p_prev = pts_cnt[(i - k_step) % N_cnt]
            p_curr = pts_cnt[i]
            p_next = pts_cnt[(i + k_step) % N_cnt]
            v_in = p_curr - p_prev
            v_out = p_next - p_curr
            n_in = np.hypot(v_in[0], v_in[1])
            n_out = np.hypot(v_out[0], v_out[1])
            if n_in > 1e-3 and n_out > 1e-3:
                cos_turn = np.clip(np.dot(v_in, v_out) / (n_in * n_out), -1.0, 1.0)
                turn_deg = np.degrees(np.arccos(cos_turn))
                internal_angles[i] = 180.0 - turn_deg
            else:
                internal_angles[i] = 180.0

        x_mid = (x_min + x_max) / 2.0
        ys_cnt = pts_cnt[:, 1]
        xs_cnt = pts_cnt[:, 0]

        # 6. АВТОМАТИЧЕСКОЕ ПРАВИЛО: ИСТИННЫЕ 4 УГЛА С УЧЕТОМ ГЕОМЕТРИЧЕСКОЙ ГЛУБИНЫ
        # P_BR: нижне-правый угол (в нижней зоне y >= 0.72*H_mask)
        cand_br = np.where((ys_cnt >= y_min + 0.72 * H_mask) & (xs_cnt >= x_mid))[0]
        i_br = cand_br[np.argmin(internal_angles[cand_br])] if len(cand_br) > 0 else int(np.argmax(xs_cnt))
        P_BR = pts_cnt[i_br].astype(np.float32)

        # P_BL: нижне-левый угол (на сопоставимой с P_BR глубине в зоне y >= 0.72*H_mask)
        cand_bl = np.where((ys_cnt >= max(y_min + 0.72 * H_mask, P_BR[1] - 0.10 * H_mask)) & (xs_cnt <= x_mid))[0]
        if len(cand_bl) > 0:
            i_bl = cand_bl[np.argmin(internal_angles[cand_bl])]
        else:
            cand_bl_all = np.where((ys_cnt >= y_min + 0.72 * H_mask) & (xs_cnt <= x_mid))[0]
            i_bl = cand_bl_all[np.argmin(internal_angles[cand_bl_all])] if len(cand_bl_all) > 0 else int(np.argmin(xs_cnt))
        P_BL = pts_cnt[i_bl].astype(np.float32)

        # P_TL: верхне-левый угол (в верхней зоне y <= 0.28*H_mask)
        cand_tl = np.where((ys_cnt <= y_min + 0.28 * H_mask) & (xs_cnt <= x_mid))[0]
        i_tl = cand_tl[np.argmin(internal_angles[cand_tl])] if len(cand_tl) > 0 else int(np.argmin(xs_cnt))
        P_TL = pts_cnt[i_tl].astype(np.float32)

        # P_TR: верхне-правый угол (на сопоставимой с P_TL высоте в зоне y <= 0.28*H_mask)
        cand_tr = np.where((ys_cnt <= max(y_min + 0.28 * H_mask, P_TL[1] + 0.10 * H_mask)) & (xs_cnt >= x_mid))[0]
        if len(cand_tr) > 0:
            i_tr = cand_tr[np.argmin(internal_angles[cand_tr])]
        else:
            cand_tr_all = np.where((ys_cnt <= y_min + 0.28 * H_mask) & (xs_cnt >= x_mid))[0]
            i_tr = cand_tr_all[np.argmin(internal_angles[cand_tr_all])] if len(cand_tr_all) > 0 else int(np.argmax(xs_cnt))
        P_TR = pts_cnt[i_tr].astype(np.float32)

        def get_cnt_segment(s_idx, e_idx):
            if (e_idx - s_idx) % N_cnt < (s_idx - e_idx) % N_cnt:
                return pts_cnt[[(s_idx + i) % N_cnt for i in range((e_idx - s_idx) % N_cnt + 1)]]
            else:
                return pts_cnt[[(s_idx - i) % N_cnt for i in range((s_idx - e_idx) % N_cnt + 1)]]

        seg_t1 = get_cnt_segment(i_tl, i_tr)
        seg_t2 = get_cnt_segment(i_tr, i_tl)
        raw_T = seg_t1 if np.mean(seg_t1[:, 1]) < np.mean(seg_t2[:, 1]) else seg_t2

        seg_b1 = get_cnt_segment(i_bl, i_br)
        seg_b2 = get_cnt_segment(i_br, i_bl)
        raw_B = seg_b1 if np.mean(seg_b1[:, 1]) > np.mean(seg_b2[:, 1]) else seg_b2

        if raw_T[0, 0] > raw_T[-1, 0]:
            raw_T = raw_T[::-1]
        if raw_B[0, 0] > raw_B[-1, 0]:
            raw_B = raw_B[::-1]

        N_pts = 60
        u_vals = np.linspace(0.0, 1.0, N_pts)
        idx_t = np.linspace(0.0, 1.0, len(raw_T))
        T_curve = np.column_stack((np.interp(u_vals, idx_t, raw_T[:, 0]), np.interp(u_vals, idx_t, raw_T[:, 1])))

        idx_b = np.linspace(0.0, 1.0, len(raw_B))
        B_curve = np.column_stack((np.interp(u_vals, idx_b, raw_B[:, 0]), np.interp(u_vals, idx_b, raw_B[:, 1])))

        # 6.5. Shelf Rail Cut / Occlusion Detector & Bottom Smile Reconstruction
        # STRICT RULE:
        # We reconstruct the bottom curve ONLY AND STRICTLY if there is a real straight-line cut (e.g. shelf rail cut).
        # In all normal cases (when the mask has its natural bottom contour), we build strictly from the mask contour!
        chord_T = (1.0 - u_vals) * P_TL[1] + u_vals * P_TR[1]
        chord_B = (1.0 - u_vals) * P_BL[1] + u_vals * P_BR[1]
        u_mid = (u_vals >= 0.30) & (u_vals <= 0.70)
        
        T_sag = float(np.mean(T_curve[u_mid, 1] - chord_T[u_mid]))
        B_sag = float(np.mean(B_curve[u_mid, 1] - chord_B[u_mid]))
        raw_B_dev = np.abs(B_curve[:, 1] - chord_B)
        max_B_dev = float(np.max(raw_B_dev))
        
        # Strict straight-line cut detection:
        # 1) Top edge has clear physical curvature (|T_sag| >= 5.0 px)
        # 2) Bottom edge is strictly a flat straight line cut (max deviation from chord <= 3.5 px OR |B_sag| <= 2.0 px)
        is_straight_line_cut = (abs(T_sag) >= 5.0) and (max_B_dev <= 3.5 or abs(B_sag) <= 2.0)
        
        if is_straight_line_cut:
            if T_sag < 0:
                # Top is frown -> bottom is smile with height equal to top sagitta
                target_B_sag = abs(T_sag)
            else:
                # Top is smile -> bottom is smile with 2.0x top sagitta
                target_B_sag = 2.0 * T_sag
                
            B_mid_y = (P_BL[1] + P_BR[1]) / 2.0
            B_curve = self._fit_monotone_semi_ellipse(
                raw_ys=B_curve[:, 1],
                P_left=P_BL,
                P_right=P_BR,
                preferred_direction="smile",
                forced_apex_y=B_mid_y + target_B_sag,
                N_pts=N_pts
            )

        # 6.6. Подавление высокочастотной ряби на верхних и нижних направляющих
        # Устраняет пиксельные ступеньки и микроколебания, предотвращая деформацию сетки 3D Coon's patch
        T_curve = self._smooth_horizontal_guide(T_curve, P_TL, P_TR, N_pts=N_pts)
        if not is_straight_line_cut:
            B_curve = self._smooth_horizontal_guide(B_curve, P_BL, P_BR, N_pts=N_pts)

        # 7. Извлечение боковых сегментов контура
        seg_l1 = get_cnt_segment(i_tl, i_bl)
        seg_l2 = get_cnt_segment(i_bl, i_tl)
        raw_L = seg_l1 if np.mean(seg_l1[:, 0]) < np.mean(seg_l2[:, 0]) else seg_l2

        seg_r1 = get_cnt_segment(i_tr, i_br)
        seg_r2 = get_cnt_segment(i_br, i_tr)
        raw_R = seg_r1 if np.mean(seg_r1[:, 0]) > np.mean(seg_r2[:, 0]) else seg_r2

        # 8. Проверка ровности образующих при углах ~180° и фильтрация резких порогов
        L_curve = self._fit_straight_lateral_guide(raw_L, P_TL, P_BL, N_pts=N_pts)
        R_curve = self._fit_straight_lateral_guide(raw_R, P_TR, P_BR, N_pts=N_pts)

        return VectorMask(
            shape_type=LabelShape.CYLINDER,
            bbox=(int(x_min), int(y_min), int(x_max - x_min), int(y_max - y_min)),
            P_TL=P_TL, P_TR=P_TR, P_BL=P_BL, P_BR=P_BR,
            T_curve=T_curve,
            B_curve=B_curve,
            L_line=L_curve,
            R_line=R_curve,
            polygon=np.vstack((T_curve, R_curve, B_curve[::-1], L_curve[::-1])).astype(np.int32),
            left_line=poly_L,
            right_line=poly_R,
            top_curve=T_curve,
            bottom_curve=B_curve
        )

    def extract_vector_mask(self, mask: np.ndarray, image: Optional[np.ndarray] = None) -> VectorMask:
        return self.vectorize(mask)

Vectorizer = MaskVectorizer
