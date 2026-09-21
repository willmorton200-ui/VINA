import sys
import os

file_path = r"d:\VINA\pipeline\vectorizer.py"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Add _extract_text_parabolas before _estimate_text_curvature
idx_est = -1
for i, line in enumerate(lines):
    if "def _estimate_text_curvature(" in line:
        idx_est = i
        break

if idx_est == -1:
    print("Could not find _estimate_text_curvature")
    sys.exit(1)

new_method = """    def _extract_text_parabolas(self, ocr_data: dict, img_w: int, img_h: int) -> list[np.ndarray]:
        \"\"\"
        Groups OCR blocks into horizontal lines and fits a parabola to the bottom edge of each line.
        Returns a list of poly1d coefficients [A, B, C].
        \"\"\"
        if not ocr_data or "text_blocks" not in ocr_data:
            return []
            
        blocks = ocr_data.get("text_blocks", [])
        if len(blocks) < 2:
            return []
            
        pts = []
        for b in blocks:
            poly = b.get("bbox", [])
            if len(poly) == 4:
                br, bl = poly[2], poly[3]
                cx = (bl[0] + br[0]) / 2.0
                cy = (bl[1] + br[1]) / 2.0
                pts.append((cx, cy))
                
        if len(pts) < 3:
            return []
            
        pts = sorted(pts, key=lambda p: p[1])
        lines = []
        current_line = [pts[0]]
        for p in pts[1:]:
            if p[1] - current_line[-1][1] < img_h * 0.05:
                current_line.append(p)
            else:
                lines.append(current_line)
                current_line = [p]
        lines.append(current_line)
        
        parabolas = []
        for line in lines:
            if len(line) >= 3:
                line.sort(key=lambda p: p[0])
                x_first, y_first = line[0]
                x_last, y_last = line[-1]
                # Only trust lines that span a decent portion of the label (at least 20%)
                if x_last - x_first > img_w * 0.2:
                    xs = np.array([p[0] for p in line], dtype=np.float64)
                    ys = np.array([p[1] for p in line], dtype=np.float64)
                    try:
                        poly = np.polyfit(xs, ys, 2)
                        parabolas.append(poly)
                    except Exception:
                        pass
        return parabolas

"""

lines.insert(idx_est, new_method)

# Now inject it into vectorize()
idx_vec_ret = -1
for i, line in enumerate(lines):
    if "return VectorMask(" in line:
        idx_vec_ret = i
        break

if idx_vec_ret != -1:
    inject_str = "        text_parabolas = self._extract_text_parabolas(ocr_data, w, h)\n\n"
    lines.insert(idx_vec_ret, inject_str)
    
    # Also add it to the return arguments
    for i in range(idx_vec_ret, len(lines)):
        if "bottom_curve=B_curve" in lines[i]:
            lines[i] = lines[i].replace("bottom_curve=B_curve", "bottom_curve=B_curve,\n            text_parabolas=text_parabolas")
            break

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Successfully patched vectorizer.py")
