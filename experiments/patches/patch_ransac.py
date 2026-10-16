import sys
import numpy as np
import random

file_path = "pipeline/vectorizer.py"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

start_marker = "            if len(valid_contours) < 3:"
end_marker = "        parabolas.sort(key=lambda x: x[0], reverse=True)"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Markers not found!")
    sys.exit(1)

new_code = """            if len(valid_contours) < 3:
                continue
                
            pts_all = []
            for c in valid_contours:
                lowest_pt = self._get_lowest_point(c)
                gx = lowest_pt[0] + x_min
                gy = lowest_pt[1] + y_min
                pts_all.append([gx, gy])
                
            pts_all = np.array(pts_all, dtype=np.float64)
            n_pts = len(pts_all)
            
            # Микро-RANSAC для контуров одной строки
            best_inliers = []
            best_poly = None
            max_inlier_count = 0
            
            # Перебираем случайные тройки (до 50 итераций)
            num_iters = min(50, n_pts * (n_pts - 1) * (n_pts - 2) // 6)
            
            for _ in range(num_iters):
                idx3 = np.random.choice(n_pts, 3, replace=False)
                sample = pts_all[idx3]
                
                # Защита от коллинеарности по X
                if abs(sample[0,0] - sample[1,0]) < 2 or abs(sample[1,0] - sample[2,0]) < 2 or abs(sample[0,0] - sample[2,0]) < 2:
                    continue
                    
                try:
                    p = np.polyfit(sample[:, 0], sample[:, 1], 2)
                    # Оцениваем все точки
                    preds = np.polyval(p, pts_all[:, 0])
                    errors = np.abs(preds - pts_all[:, 1])
                    inliers = pts_all[errors < 4.0] # 4 пикселя допуск
                    
                    if len(inliers) > max_inlier_count:
                        max_inlier_count = len(inliers)
                        best_inliers = inliers
                        best_poly = p
                except np.linalg.LinAlgError:
                    continue
                    
            if max_inlier_count >= 3 and best_poly is not None:
                # Финальный фит по всем инлайнерам
                try:
                    final_poly = np.polyfit(best_inliers[:, 0], best_inliers[:, 1], 2)
                    if abs(final_poly[0]) < 0.005:
                        parabolas.append((w, final_poly, best_inliers))
                except Exception as e:
                    print(f"[Vectorizer] RANSAC final fit failed: {e}")
                
"""

new_content = content[:start_idx] + new_code + content[end_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Patch applied successfully.")
