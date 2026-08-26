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
                delta_final = max(delta_edge, 4.0)
            elif preferred_direction == "frown":
                delta_final = min(delta_edge, -4.0)
            else:
                delta_final = delta_edge
        
        # 3. Construct canonical semi-ellipse
        theta = np.linspace(0.0, np.pi, N_pts)
        x0 = (P_left[0] + P_right[0]) / 2.0
        a = max(abs(P_right[0] - P_left[0]) / 2.0, 1.0)
        
        ell_x = x0 - a * np.cos(theta)
        tilt = (1.0 - theta / np.pi) * P_left[1] + (theta / np.pi) * P_right[1] - y_corner_avg
        ell_y = y_corner_avg + delta_final * np.sin(theta) + tilt
        ell_y[0] = P_left[1]
        ell_y[-1] = P_right[1]
        
        return np.column_stack((ell_x, ell_y))

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

        # 3. Fit Lateral Tangent Lines (Касательные образующие цилиндра x = m*y + c)
        # Use middle 60% of mask height for stable regression
        L_mid = left_pts[(left_pts[:, 1] >= y_min + 0.20 * H_mask) & (left_pts[:, 1] <= y_min + 0.80 * H_mask)]
        R_mid = right_pts[(right_pts[:, 1] >= y_min + 0.20 * H_mask) & (right_pts[:, 1] <= y_min + 0.80 * H_mask)]

        if len(L_mid) >= 10:
            poly_L = np.polyfit(L_mid[:, 1], L_mid[:, 0], deg=1)
        else:
            poly_L = np.array([0.0, float(x_min)])

        if len(R_mid) >= 10:
            poly_R = np.polyfit(R_mid[:, 1], R_mid[:, 0], deg=1)
        else:
            poly_R = np.array([0.0, float(x_max)])

        # 4. Compute Intersection Points between Horizontal Profiles & Lateral Tangents
        # Top reference level
        top_ys = [pt[1] for pt in left_pts if pt[1] <= y_min + 0.15 * H_mask]
        y_top_ref = float(np.median(top_ys)) if len(top_ys) > 0 else float(y_min)

        # Compute widths for stable bottom inflection detection
        widths = {int(y): right_pts[idx][0] - left_pts[idx][0] for idx, y in enumerate(valid_ys)}
        max_w = max(widths.values()) if widths else 1.0

        # Bottom-left transition inflection
        lower_left = left_pts[(left_pts[:, 1] >= y_min + 0.50 * H_mask) & (left_pts[:, 1] <= y_min + 0.90 * H_mask)]
        if len(lower_left) > 0:
            y_bl_ref = float(lower_left[np.argmin(lower_left[:, 0] - 0.05 * lower_left[:, 1])][1])
        else:
            y_bl_ref = float(y_max)

        # Bottom-right transition inflection (lowest y in lower section where width >= 0.70 * max_w)
        lower_br_candidates = [y for y in valid_ys if y >= y_min + 0.50 * H_mask and y <= y_min + 0.92 * H_mask and widths[y] >= 0.70 * max_w]
        if lower_br_candidates:
            y_br_ref = float(max(lower_br_candidates))
        else:
            y_br_ref = float(y_max - 0.15 * H_mask)

        # Exact Intersection Corners:
        P_TL = np.array([poly_L[0] * y_top_ref + poly_L[1], y_top_ref])
        P_TR = np.array([poly_R[0] * y_top_ref + poly_R[1], y_top_ref])
        P_BL = np.array([poly_L[0] * y_bl_ref + poly_L[1], y_bl_ref])
        P_BR = np.array([poly_R[0] * y_br_ref + poly_R[1], y_br_ref])

        # 5. Extract Raw Profiles along horizontal spans
        N_pts = 60
        xs_top = np.linspace(P_TL[0], P_TR[0], N_pts)
        raw_ys_top = []
        for x in xs_top:
            x_int = int(np.clip(round(x), 0, w - 1))
            col_ys = np.where(mask_closed[:, x_int] > 127)[0]
            raw_ys_top.append(float(np.min(col_ys)) if len(col_ys) > 0 else P_TL[1])
        raw_ys_top = np.array(raw_ys_top)

        xs_bot = np.linspace(P_BL[0], P_BR[0], N_pts)
        raw_ys_bot = []
        for x in xs_bot:
            x_int = int(np.clip(round(x), 0, w - 1))
            col_ys = np.where(mask_closed[:, x_int] > 127)[0]
            raw_ys_bot.append(float(np.max(col_ys)) if len(col_ys) > 0 else P_BL[1])
        raw_ys_bot = np.array(raw_ys_bot)

        # 6. Fit Canonical Monotone Semi-Ellipses (Шаг 3)
        y_bot_apex = float(np.max(raw_ys_bot))
        T_curve = self._fit_monotone_semi_ellipse(raw_ys_top, P_TL, P_TR, preferred_direction="smile", N_pts=N_pts)
        B_curve = self._fit_monotone_semi_ellipse(raw_ys_bot, P_BL, P_BR, preferred_direction="smile", forced_apex_y=y_bot_apex, N_pts=N_pts)

        # 7. Lateral Polyline Connectors
        v_vals = np.linspace(0.0, 1.0, N_pts)
        L_curve = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
        R_curve = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR

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
