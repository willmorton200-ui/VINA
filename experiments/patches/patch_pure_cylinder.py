import sys
import numpy as np

file_path = "pipeline/dewarp_engine.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "# 4. VINA 3.0: Continuous Cylindrical Parameterization with Text Guides"
end_marker = "for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Markers not found!")
    sys.exit(1)

new_code = """# 4. VINA 3.0: Pure Cylinder Mathematical Parameterization ("Штрихи художника")
        grid_cols = 32
        u_norm_prof = np.linspace(0.0, 1.0, grid_cols)
        profile_blended = 0.5 * np.sin(np.pi * u_norm_prof) + 0.5 * (4.0 * u_norm_prof * (1.0 - u_norm_prof))
        
        # 1. Вычисляем центральную ось цилиндра по RANSAC-направляющим
        # Ось цилиндра задает базовый наклон бутылки
        dx_L = vec.L_line[-1, 0] - vec.L_line[0, 0]
        dy_L = vec.L_line[-1, 1] - vec.L_line[0, 1]
        m_L = dx_L / dy_L if abs(dy_L) > 1e-5 else 0.0
        
        dx_R = vec.R_line[-1, 0] - vec.R_line[0, 0]
        dy_R = vec.R_line[-1, 1] - vec.R_line[0, 1]
        m_R = dx_R / dy_R if abs(dy_R) > 1e-5 else 0.0
        
        m_axis = (m_L + m_R) / 2.0
        m_chord = -m_axis  # Перпендикулярная хорда (горизонталь цилиндра)
        
        # Референсная точка оси
        X_ref = (vec.L_line[0, 0] + vec.R_line[0, 0]) / 2.0
        Y_ref = (vec.L_line[0, 1] + vec.R_line[0, 1]) / 2.0
        P_TL_axis = (vec.L_line[0, 0], vec.L_line[0, 1])
        P_TR_axis = (vec.R_line[0, 0], vec.R_line[0, 1])
        
        def get_chord_endpoints(Y_axis):
            # Точка на оси
            X_axis = X_ref + m_axis * (Y_axis - Y_ref)
            
            # Левое пересечение
            denom_L = 1.0 - m_chord * m_L
            if abs(denom_L) < 1e-5: denom_L = 1e-5
            y_L = (Y_axis + m_chord * (P_TL_axis[0] - X_axis) - m_chord * m_L * P_TL_axis[1]) / denom_L
            x_L = P_TL_axis[0] + m_L * (y_L - P_TL_axis[1])
            
            # Правое пересечение
            denom_R = 1.0 - m_chord * m_R
            if abs(denom_R) < 1e-5: denom_R = 1e-5
            y_R = (Y_axis + m_chord * (P_TR_axis[0] - X_axis) - m_chord * m_R * P_TR_axis[1]) / denom_R
            x_R = P_TR_axis[0] + m_R * (y_R - P_TR_axis[1])
            
            return (x_L, y_L), (x_R, y_R)

        v_points = []
        delta_points = []
        text_data = []
        
        # Функция для проверки и извлечения точки консенсуса
        def process_curve_for_consensus(curve_pts, is_text, poly=None):
            idx_mid = len(curve_pts) // 2
            Y_axis = curve_pts[idx_mid, 1]
            (x_L, y_L), (x_R, y_R) = get_chord_endpoints(Y_axis)
            
            # Фактический наклон хорды этого штриха
            actual_chord_m = (curve_pts[-1, 1] - curve_pts[0, 1]) / (curve_pts[-1, 0] - curve_pts[0, 0] + 1e-5)
            # Отклонение от идеальной ортогональной хорды
            angle_diff = np.degrees(np.arctan(abs((actual_chord_m - m_chord) / (1 + actual_chord_m * m_chord))))
            
            if angle_diff <= 15.0:
                actual_delta = curve_pts[idx_mid, 1] - (curve_pts[0, 1] + curve_pts[-1, 1]) / 2.0
                v_points.append(Y_axis)
                delta_points.append(actual_delta)
                if is_text:
                    text_data.append({"Y_axis": Y_axis, "actual_delta": actual_delta})
                    
        # Проверяем T_curve и B_curve (если они не диагональные срезы - берем в консенсус)
        process_curve_for_consensus(vec.T_curve, is_text=False)
        process_curve_for_consensus(vec.B_curve, is_text=False)
        
        # Проверяем текстовые параболы
        if hasattr(vec, 'text_parabolas') and vec.text_parabolas:
            for poly in vec.text_parabolas:
                # Оцениваем Y_axis по центру бутылки
                Y_axis_approx = np.polyval(poly, X_ref)
                (x_L, y_L), (x_R, y_R) = get_chord_endpoints(Y_axis_approx)
                x_base = np.linspace(x_L, x_R, grid_cols)
                ys = np.polyval(poly, x_base)
                
                curve_pts = np.column_stack((x_base, ys))
                process_curve_for_consensus(curve_pts, is_text=True)
                
        v_points = np.array(v_points)
        delta_points = np.array(delta_points)
        
        best_m = 0.0
        best_c = 0.0
        
        if len(v_points) >= 3:
            max_inliers = 0
            best_err = float('inf')
            
            for i in range(len(v_points)):
                for j in range(i+1, len(v_points)):
                    dv = v_points[j] - v_points[i]
                    if abs(dv) < 10.0:
                        continue
                        
                    m = (delta_points[j] - delta_points[i]) / dv
                    c = delta_points[i] - m * v_points[i]
                    
                    preds = m * v_points + c
                    errors = np.abs(preds - delta_points)
                    inliers = np.sum(errors < 8.0) # 8px tolerance
                    
                    if inliers > max_inliers or (inliers == max_inliers and np.mean(errors[errors < 8.0]) < best_err):
                        max_inliers = inliers
                        best_err = np.mean(errors[errors < 8.0]) if inliers > 0 else float('inf')
                        best_m = m
                        best_c = c
        elif len(v_points) == 2:
            dv = v_points[1] - v_points[0]
            if abs(dv) > 10.0:
                best_m = (delta_points[1] - delta_points[0]) / dv
                best_c = delta_points[0] - best_m * v_points[0]
        elif len(v_points) == 1:
            best_c = delta_points[0]

        # 3. Генерация сетки строго по цилиндру, отвязанной от углов P_TL/P_BL
        # Ограничение по высоте берем от маски (vec.bbox)
        target_y_min = max(0, vec.bbox[1] - 20)
        target_y_max = min(h_c - 1, vec.bbox[1] + vec.bbox[3] + 20)
        
        # Чтобы покрыть весь диапазон Y с учетом наклона оси, пускаем Y_axis от min до max
        grid_rows_ext = int((target_y_max - target_y_min) / 4.0) # approx 4 pixels per row
        grid_rows_ext = max(grid_rows_ext, 10)
        y_g = np.linspace(target_y_min, target_y_max, grid_rows_ext)
        
        def create_perfect_curve(Y_axis):
            (x_L, y_L), (x_R, y_R) = get_chord_endpoints(Y_axis)
            x_base = (1.0 - u_norm_prof) * x_L + u_norm_prof * x_R
            y_base = (1.0 - u_norm_prof) * y_L + u_norm_prof * y_R
            
            target_delta = best_m * Y_axis + best_c
            ys_perfect = y_base + target_delta * profile_blended
            return np.column_stack((x_base, ys_perfect))
            
        u_grid = np.zeros((grid_rows_ext, grid_cols), dtype=np.float32)
        v_grid = np.zeros((grid_rows_ext, grid_cols), dtype=np.float32)
        
        for r in range(grid_rows_ext):
            curve = create_perfect_curve(y_g[r])
            u_grid[r, :] = np.clip(curve[:, 0], 0, w_c - 1)
            v_grid[r, :] = np.clip(curve[:, 1], 0, h_c - 1)
            
        guides = []
        # Top guide 
        curve_T_perfect = create_perfect_curve(target_y_min + 20)
        guides.append({"v": target_y_min + 20, "curve": curve_T_perfect})
        
        # Text guides for visualization
        for td in text_data:
            err = abs(td["actual_delta"] - (best_m * td["Y_axis"] + best_c))
            if err < 15.0:
                curve_txt = create_perfect_curve(td["Y_axis"])
                guides.append({"v": td["Y_axis"], "curve": curve_txt, "is_text": True})
                
        # Bottom guide
        curve_B_perfect = create_perfect_curve(target_y_max - 20)
        guides.append({"v": target_y_max - 20, "curve": curve_B_perfect})
        
        arc_T = np.sum(np.hypot(np.diff(curve_T_perfect[:, 0]), np.diff(curve_T_perfect[:, 1])))
        arc_B = np.sum(np.hypot(np.diff(curve_B_perfect[:, 0]), np.diff(curve_B_perfect[:, 1])))
        dst_w = max(int(round(max(arc_T, arc_B))), 100)
        
        # Длина по оси
        dst_h = max(int(round(target_y_max - target_y_min)), 100)
        
        map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        dewarped = cv2.remap(rot_img, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
        
        # Diagnostic visual features
        vis_features = rot_img.copy()
        ext_L = vec.L_line
        ext_R = vec.R_line
        
        cv2.polylines(vis_features, [ext_L.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [ext_R.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [curve_T_perfect.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [curve_B_perfect.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
        
        # Draw text parabolas if they exist
        for g in guides:
            if g.get("is_text"):
                cv2.polylines(vis_features, [g["curve"].astype(np.int32)], False, (0, 0, 255), 2, cv2.LINE_AA)
                
        """

new_content = content[:start_idx] + new_code + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patch applied successfully.")
