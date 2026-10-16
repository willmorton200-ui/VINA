import sys
import numpy as np

file_path = "pipeline/dewarp_engine.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "# 4. VINA 3.0: Pure Cylinder Mathematical Parameterization (\"Штрихи художника\")"
end_marker = "for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Markers not found!")
    sys.exit(1)

new_code = """# 4. VINA 3.0: Artist Strokes Parameterization (Multi-segment Coon's Patch)
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
        
        def add_curve_if_valid(curve_pts, is_text):
            # curve_pts shape (N, 2)
            actual_chord_m = (curve_pts[-1, 1] - curve_pts[0, 1]) / (curve_pts[-1, 0] - curve_pts[0, 0] + 1e-5)
            angle_diff = np.degrees(np.arctan(abs((actual_chord_m - m_chord_ortho) / (1 + actual_chord_m * m_chord_ortho))))
            
            if angle_diff <= 15.0:
                valid_curves.append(curve_pts)
                guides.append({"v": np.mean(curve_pts[:, 1]), "curve": curve_pts, "is_text": is_text})
                
        # T_curve и B_curve
        add_curve_if_valid(vec.T_curve, is_text=False)
        add_curve_if_valid(vec.B_curve, is_text=False)
        
        # Текстовые параболы
        if hasattr(vec, 'text_parabolas') and vec.text_parabolas:
            for poly in vec.text_parabolas:
                x_L, y_L = intersect_parabola_with_lateral(poly, is_left=True)
                x_R, y_R = intersect_parabola_with_lateral(poly, is_left=False)
                
                # Если парабола вырождена или перевернута, пропускаем
                if x_R <= x_L: continue
                
                x_base = np.linspace(x_L, x_R, grid_cols)
                ys = np.polyval(poly, x_base)
                curve_pts = np.column_stack((x_base, ys))
                
                add_curve_if_valid(curve_pts, is_text=True)
                
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
            
        arc_T = np.sum(np.hypot(np.diff(u_grid[0, :]), np.diff(v_grid[0, :])))
        arc_B = np.sum(np.hypot(np.diff(u_grid[-1, :]), np.diff(v_grid[-1, :])))
        dst_w = max(int(round(max(arc_T, arc_B))), 100)
        dst_h = max(int(round(target_y_max - target_y_min)), 100)
        
        map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        dewarped = cv2.remap(rot_img, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
        
        # Diagnostic visual features
        vis_features = rot_img.copy()
        
        cv2.polylines(vis_features, [vec.L_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [vec.R_line.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        
        # Отрисовка всех валидных штрихов
        for g in guides:
            color = (0, 0, 255) if g.get("is_text") else (0, 255, 0)
            cv2.polylines(vis_features, [g["curve"].astype(np.int32)], False, color, 2, cv2.LINE_AA)
            
        """

new_content = content[:start_idx] + new_code + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patch applied successfully.")
