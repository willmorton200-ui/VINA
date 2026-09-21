import sys

file_path = "pipeline/dewarp_engine.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define start and end markers
start_marker = "# 4. VINA 3.0: Continuous Cylindrical Parameterization with Text Guides"
end_marker = "for pt in [vec.P_TL, vec.P_TR, vec.P_BL, vec.P_BR]:"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Markers not found!")
    sys.exit(1)

new_code = """# 4. VINA 3.0: Continuous Cylindrical Parameterization with Text Guides
        grid_cols = 32
        
        u_g = np.linspace(0.0, 1.0, grid_cols)
        u_vals = np.linspace(0.0, 1.0, len(vec.T_curve))
        T_res = np.column_stack((np.interp(u_g, u_vals, vec.T_curve[:, 0]), np.interp(u_g, u_vals, vec.T_curve[:, 1])))
        B_res = np.column_stack((np.interp(u_g, u_vals, vec.B_curve[:, 0]), np.interp(u_g, u_vals, vec.B_curve[:, 1])))
        
        # VINA 3.0: Global Perspective Consensus
        mid_idx = grid_cols // 2
        delta_T = T_res[mid_idx, 1] - (T_res[0, 1] + T_res[-1, 1]) / 2.0
        delta_B = B_res[mid_idx, 1] - (B_res[0, 1] + B_res[-1, 1]) / 2.0
        
        v_points = [0.0, 1.0]
        delta_points = [delta_T, delta_B]
        text_data = []
        
        if hasattr(vec, 'text_parabolas') and vec.text_parabolas:
            for poly in vec.text_parabolas:
                y_center = np.polyval(poly, (vec.P_TL[0] + vec.P_TR[0]) / 2.0)
                v_est = (y_center - vec.P_TL[1]) / (vec.P_BL[1] - vec.P_TL[1] + 1e-5)
                
                if 0.05 < v_est < 0.95:
                    x_base = (1.0 - v_est) * T_res[:, 0] + v_est * B_res[:, 0]
                    ys = np.polyval(poly, x_base)
                    actual_delta = ys[mid_idx] - (ys[0] + ys[-1]) / 2.0
                    
                    text_data.append({
                        "v": float(v_est),
                        "actual_delta": float(actual_delta),
                        "x_base": x_base,
                        "y_left": ys[0],
                        "y_right": ys[-1]
                    })
                    v_points.append(float(v_est))
                    delta_points.append(float(actual_delta))
                    
        v_points = np.array(v_points)
        delta_points = np.array(delta_points)
        
        # Robust linear fit: delta(v) = m*v + c
        best_m = delta_B - delta_T
        best_c = delta_T
        
        if len(v_points) >= 3:
            max_inliers = 0
            best_err = float('inf')
            
            for i in range(len(v_points)):
                for j in range(i+1, len(v_points)):
                    dv = v_points[j] - v_points[i]
                    if abs(dv) < 0.05:
                        continue
                        
                    m = (delta_points[j] - delta_points[i]) / dv
                    c = delta_points[i] - m * v_points[i]
                    
                    preds = m * v_points + c
                    errors = np.abs(preds - delta_points)
                    inliers = np.sum(errors < 6.0) # 6px tolerance
                    
                    if inliers > max_inliers or (inliers == max_inliers and np.mean(errors[errors < 6.0]) < best_err):
                        max_inliers = inliers
                        best_err = np.mean(errors[errors < 6.0]) if inliers > 0 else float('inf')
                        best_m = m
                        best_c = c

        # Enforce the mathematical model for all guides & global unroll
        y_label_top = (vec.P_TL[1] + vec.P_TR[1]) / 2.0
        y_label_bot = (vec.P_BL[1] + vec.P_BR[1]) / 2.0
        label_h = y_label_bot - y_label_top + 1e-5
        
        target_y_min = max(0, min(vec.P_TL[1], vec.P_TR[1]) - 20)
        target_y_max = min(h_c - 1, max(vec.P_BL[1], vec.P_BR[1]) + 20)
        
        v_min = (target_y_min - y_label_top) / label_h
        v_max = (target_y_max - y_label_top) / label_h
        
        grid_rows_ext = int(24 * (v_max - v_min))
        grid_rows_ext = max(grid_rows_ext, 10)
        v_g = np.linspace(v_min, v_max, grid_rows_ext)

        u_norm_prof = np.linspace(0.0, 1.0, grid_cols)
        profile_blended = 0.5 * np.sin(np.pi * u_norm_prof) + 0.5 * (4.0 * u_norm_prof * (1.0 - u_norm_prof))
        
        def create_perfect_curve(x_base, y_left, y_right, v):
            target_delta = best_m * v + best_c
            baseline = (1.0 - u_norm_prof) * y_left + u_norm_prof * y_right
            ys_perfect = baseline + target_delta * profile_blended
            return np.column_stack((x_base, ys_perfect))
            
        u_grid = np.zeros((grid_rows_ext, grid_cols), dtype=np.float32)
        v_grid = np.zeros((grid_rows_ext, grid_cols), dtype=np.float32)
        
        for r in range(grid_rows_ext):
            v_val = v_g[r]
            y_l = (1.0 - v_val) * vec.P_TL[1] + v_val * vec.P_BL[1]
            y_r = (1.0 - v_val) * vec.P_TR[1] + v_val * vec.P_BR[1]
            x_l = (1.0 - v_val) * vec.P_TL[0] + v_val * vec.P_BL[0]
            x_r = (1.0 - v_val) * vec.P_TR[0] + v_val * vec.P_BR[0]
            
            x_base = (1.0 - u_g) * x_l + u_g * x_r
            curve = create_perfect_curve(x_base, y_l, y_r, v_val)
            
            u_grid[r, :] = np.clip(curve[:, 0], 0, w_c - 1)
            v_grid[r, :] = np.clip(curve[:, 1], 0, h_c - 1)
            
        guides = []
        # Top guide (v=0.0)
        curve_T = create_perfect_curve(T_res[:, 0], vec.P_TL[1], vec.P_TR[1], 0.0)
        guides.append({"v": 0.0, "curve": curve_T})
        
        # Text guides for visualization
        for td in text_data:
            err = abs(td["actual_delta"] - (best_m * td["v"] + best_c))
            if err < 15.0:
                y_l = (1.0 - td["v"]) * vec.P_TL[1] + td["v"] * vec.P_BL[1]
                y_r = (1.0 - td["v"]) * vec.P_TR[1] + td["v"] * vec.P_BR[1]
                curve_txt = create_perfect_curve(td["x_base"], y_l, y_r, td["v"])
                guides.append({"v": td["v"], "curve": curve_txt, "is_text": True})
                
        # Bottom guide (v=1.0)
        curve_B = create_perfect_curve(B_res[:, 0], vec.P_BL[1], vec.P_BR[1], 1.0)
        guides.append({"v": 1.0, "curve": curve_B})
        
        arc_T = np.sum(np.hypot(np.diff(curve_T[:, 0]), np.diff(curve_T[:, 1])))
        arc_B = np.sum(np.hypot(np.diff(curve_B[:, 0]), np.diff(curve_B[:, 1])))
        dst_w = max(int(round(max(arc_T, arc_B))), 100)
        
        len_L_ext = np.hypot(vec.P_TL[0] - vec.P_BL[0], vec.P_TL[1] - vec.P_BL[1]) * (v_max - v_min)
        len_R_ext = np.hypot(vec.P_TR[0] - vec.P_BR[0], vec.P_TR[1] - vec.P_BR[1]) * (v_max - v_min)
        dst_h = max(int(round(max(len_L_ext, len_R_ext))), 100)
        
        map_x = cv2.resize(u_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        map_y = cv2.resize(v_grid, (dst_w, dst_h), interpolation=cv2.INTER_CUBIC)
        dewarped = cv2.remap(rot_img, map_x.astype(np.float32), map_y.astype(np.float32), interpolation=cv2.INTER_LANCZOS4)
        
        # Diagnostic visual features
        vis_features = rot_img.copy()
        ext_L = np.array([[(1.0 - v_min) * vec.P_TL[0] + v_min * vec.P_BL[0], (1.0 - v_min) * vec.P_TL[1] + v_min * vec.P_BL[1]],
                          [(1.0 - v_max) * vec.P_TL[0] + v_max * vec.P_BL[0], (1.0 - v_max) * vec.P_TL[1] + v_max * vec.P_BL[1]]])
        ext_R = np.array([[(1.0 - v_min) * vec.P_TR[0] + v_min * vec.P_BR[0], (1.0 - v_min) * vec.P_TR[1] + v_min * vec.P_BR[1]],
                          [(1.0 - v_max) * vec.P_TR[0] + v_max * vec.P_BR[0], (1.0 - v_max) * vec.P_TR[1] + v_max * vec.P_BR[1]]])
        
        cv2.polylines(vis_features, [ext_L.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [ext_R.astype(np.int32)], False, (255, 160, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [curve_T.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
        cv2.polylines(vis_features, [curve_B.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
        
        # Draw text parabolas if they exist
        for g in guides:
            if g.get("is_text"):
                cv2.polylines(vis_features, [g["curve"].astype(np.int32)], False, (0, 0, 255), 2, cv2.LINE_AA)
                
        """

new_content = content[:start_idx] + new_code + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patch applied successfully.")
