import sys

file_path = "pipeline/vectorizer.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "        # 6. АВТОМАТИЧЕСКОЕ УНИВЕРСАЛЬНОЕ ПРАВИЛО: МИНИМАЛЬНЫЙ ВНУТРЕННИЙ УГОЛ КОНТУРА"
end_marker = "        def get_cnt_segment(s_idx, e_idx):"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Markers not found!")
    sys.exit(1)

new_code = """        # 6. RANSAC Robust Lateral Guides (VINA 3.0)
        x_mid = (x_min + x_max) / 2.0
        
        def _fit_robust_vertical_line(pts: np.ndarray, max_angle_deg: float = 15.0) -> tuple:
            best_inliers = 0
            best_line = None
            best_err = float('inf')
            N = len(pts)
            if N < 2:
                return (0.0, 1.0, pts[0][0], pts[0][1])
                
            import random
            max_m = np.tan(np.radians(max_angle_deg))
            
            for _ in range(100):
                idx1, idx2 = random.sample(range(N), 2)
                p1, p2 = pts[idx1], pts[idx2]
                dy = p2[1] - p1[1]
                dx = p2[0] - p1[0]
                
                if abs(dy) < 1e-3:
                    continue
                    
                m = dx / dy
                if abs(m) > max_m:
                    continue
                    
                x0, y0 = p1
                preds_x = m * (pts[:, 1] - y0) + x0
                errors = np.abs(pts[:, 0] - preds_x)
                inliers = np.sum(errors < 8.0) # 8px tolerance for masking artifacts
                
                if inliers > best_inliers or (inliers == best_inliers and np.mean(errors[errors < 8.0]) < best_err):
                    best_inliers = inliers
                    best_err = np.mean(errors[errors < 8.0]) if inliers > 0 else float('inf')
                    vy = 1.0
                    vx = m
                    norm = np.hypot(vx, vy)
                    best_line = (vx/norm, vy/norm, x0, y0)
                    
            if best_line is None:
                return (0.0, 1.0, np.mean(pts[:, 0]), np.mean(pts[:, 1]))
            return best_line

        left_pts = pts_cnt[pts_cnt[:, 0] <= x_mid]
        right_pts = pts_cnt[pts_cnt[:, 0] > x_mid]
        
        line_L = _fit_robust_vertical_line(left_pts, max_angle_deg=15.0)
        line_R = _fit_robust_vertical_line(right_pts, max_angle_deg=15.0)
        
        def get_inliers_extremes(pts, line, tolerance=10.0):
            vx, vy, x0, y0 = line
            m = vx / (vy + 1e-6)
            preds_x = m * (pts[:, 1] - y0) + x0
            errors = np.abs(pts[:, 0] - preds_x)
            inliers = pts[errors < tolerance]
            if len(inliers) == 0:
                inliers = pts
            inliers = inliers[np.argsort(inliers[:, 1])]
            return inliers[0].astype(np.float32), inliers[-1].astype(np.float32)
            
        P_TL_raw, P_BL_raw = get_inliers_extremes(left_pts, line_L)
        P_TR_raw, P_BR_raw = get_inliers_extremes(right_pts, line_R)
        
        def project_to_line(pt, line):
            vx, vy, x0, y0 = line
            m = vx / (vy + 1e-6)
            new_x = m * (pt[1] - y0) + x0
            return np.array([new_x, pt[1]], dtype=np.float32)
            
        P_TL = project_to_line(P_TL_raw, line_L)
        P_BL = project_to_line(P_BL_raw, line_L)
        P_TR = project_to_line(P_TR_raw, line_R)
        P_BR = project_to_line(P_BR_raw, line_R)
        
        i_tl = int(np.argmin(np.hypot(pts_cnt[:, 0] - P_TL_raw[0], pts_cnt[:, 1] - P_TL_raw[1])))
        i_bl = int(np.argmin(np.hypot(pts_cnt[:, 0] - P_BL_raw[0], pts_cnt[:, 1] - P_BL_raw[1])))
        i_tr = int(np.argmin(np.hypot(pts_cnt[:, 0] - P_TR_raw[0], pts_cnt[:, 1] - P_TR_raw[1])))
        i_br = int(np.argmin(np.hypot(pts_cnt[:, 0] - P_BR_raw[0], pts_cnt[:, 1] - P_BR_raw[1])))

"""

new_content = content[:start_idx] + new_code + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patch applied successfully.")
