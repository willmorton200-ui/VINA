import cv2
import numpy as np

# 1. Load mask and color image
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# 2. Side Tangent lines (True Left and Right generators of cylinder)
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64

y_min = 116.0
y_max = 1557.0

# Cylinder Central Axis: x_c(y)
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

# 3. TOP ELLIPSE (Upper rim of cylinder)
# Radius a_top = (x_r_top - x_l_top) / 2
x_l_top = m_l * y_min + c_l
x_r_top = m_r * y_min + c_r
a_top = (x_r_top - x_l_top) / 2.0
xc_top = (x_l_top + x_r_top) / 2.0
y0_top = y_min  # apex at top

# Minor radius b_top from top mask curvature:
# Near apex, y(x) ≈ y0 + (b / (2 * a^2)) * (x - xc)^2
# We know poly curvature k ≈ 0.000494 => b_top ≈ k * a_top^2
b_top = 0.0004938 * (a_top ** 2)
print(f"Top Ellipse: center=({xc_top:.1f}, {y0_top + b_top:.1f}), a={a_top:.1f}, b={b_top:.1f}")

# 4. TEXT ROW ELLIPSES (ALMA VALLEY and РОССИЯ / КРЫМ)
# Binarize crop to find text letters
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
binary_mask = cv2.bitwise_and(binary, mask)

num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask)

# Find bottom-most text row (РОССИЯ / КРЫМ)
lowest_text_pts = []
for i in range(1, num_labels):
    bx, by, bw, bh, area = stats[i]
    if by > y_min + (y_max - y_min) * 0.70 and 5 < bh < 80 and 5 < bw < 80 and area > 20:
        lowest_text_pts.append([bx + bw / 2.0, by + bh])

lowest_text_pts = np.array(lowest_text_pts, dtype=np.float32)

# Text row height
y_text_row = float(np.median(lowest_text_pts[:, 1]))
x_l_text = m_l * y_text_row + c_l
x_r_text = m_r * y_text_row + c_r
a_text = (x_r_text - x_l_text) / 2.0
xc_text = (x_l_text + x_r_text) / 2.0

# Fit ellipse minor axis b_text from the points: y_i = y0_text + b_text * (1 - sqrt(1 - ((x_i - xc_text)/a_text)^2))
dx_norm = np.clip((lowest_text_pts[:, 0] - xc_text) / a_text, -0.99, 0.99)
sagitta_norm = 1.0 - np.sqrt(1.0 - dx_norm ** 2)

# Linear regression for y0 and b_text: y_i = y0 + b_text * sagitta_norm
res = np.polyfit(sagitta_norm, lowest_text_pts[:, 1], deg=1)
b_text = abs(float(res[0]))
y0_text = float(res[1])
print(f"Bottom Text Ellipse: xc={xc_text:.1f}, a={a_text:.1f}, b={b_text:.1f}, y0={y0_text:.1f}")

# 5. TRUE BOTTOM GUIDE ELLIPSE (Extrapolated to bottom extent y_max)
x_l_bot = m_l * y_max + c_l
x_r_bot = m_r * y_max + c_r
a_bot = (x_r_bot - x_l_bot) / 2.0
xc_bot = (x_l_bot + x_r_bot) / 2.0
b_bot = b_text * (a_bot / a_text) # perspective scaling of ellipse minor axis
y0_bot = y_max - b_bot            # apex touches bottom

print(f"True Bottom Ellipse: xc={xc_bot:.1f}, a={a_bot:.1f}, b={b_bot:.1f}")

# -------------------------------------------------------------
# 6. RENDER ARCHITECTURAL ELLIPSE DRAWING ON MASK
# -------------------------------------------------------------
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

# Draw central cylinder axis (Red dashed line)
y_axis = np.linspace(y_min - 60, y_max + 60, 200)
for y_a in range(int(y_min - 60), int(y_max + 60), 12):
    x_a = int(m_c * y_a + c_c)
    cv2.line(vis, (x_a, y_a), (x_a, y_a + 6), (0, 0, 255), 2, cv2.LINE_AA)

# Draw Blue side tangents (Generators)
eval_ys = np.linspace(y_min - 40, y_max + 40, 100)
left_line = np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)
right_line = np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)
cv2.polylines(vis, [left_line], False, (255, 140, 0), 5, lineType=cv2.LINE_AA)
cv2.polylines(vis, [right_line], False, (255, 140, 0), 5, lineType=cv2.LINE_AA)

def draw_perspective_ellipse(img, xc, yc_center, a, b, color_front=(0, 0, 255), color_back=(0, 0, 180)):
    # Front visible half-ellipse (solid)
    thetas_front = np.linspace(0, np.pi, 100)
    xs_f = xc + a * np.cos(thetas_front)
    ys_f = yc_center + b * np.sin(thetas_front)
    pts_f = np.column_stack((xs_f, ys_f)).astype(np.int32)
    cv2.polylines(img, [pts_f], False, color_front, 4, lineType=cv2.LINE_AA)
    
    # Back hidden half-ellipse (dashed)
    thetas_back = np.linspace(np.pi, 2 * np.pi, 50)
    xs_b = xc + a * np.cos(thetas_back)
    ys_b = yc_center + b * np.sin(thetas_back)
    for k in range(0, len(xs_b) - 1, 2):
        p1 = (int(xs_b[k]), int(ys_b[k]))
        p2 = (int(xs_b[k+1]), int(ys_b[k+1]))
        cv2.line(img, p1, p2, color_back, 2, cv2.LINE_AA)

# Draw Top Ellipse (front solid, back dashed)
draw_perspective_ellipse(vis, xc_top, y0_top + b_top, a_top, b_top, color_front=(0, 0, 255), color_back=(0, 0, 200))

# Draw Text Baseline Ellipse
draw_perspective_ellipse(vis, xc_text, y0_text + b_text, a_text, b_text, color_front=(0, 255, 255), color_back=(0, 180, 180))

# Draw True Bottom Guide Ellipse
draw_perspective_ellipse(vis, xc_bot, y0_bot + b_bot, a_bot, b_bot, color_front=(0, 0, 255), color_back=(0, 0, 200))

# Draw text bottom points (Yellow dots on the ellipse)
for pt in lowest_text_pts:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 4, (0, 255, 255), -1, cv2.LINE_AA)

# Draw shelf occlusion line (Flat red line at bottom to highlight the defect)
cv2.line(vis, (int(x_l_bot - 20), int(y_max)), (int(x_r_bot + 20), int(y_max)), (50, 50, 255), 2, cv2.LINE_AA)
cv2.putText(vis, "Shelf Cutoff (Ignored)", (int(x_l_bot + 40), int(y_max + 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 255), 2)

out_ellipse_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\cylinder_ellipses_architectural.png"
cv2.imwrite(out_ellipse_path, vis)
print(f"Saved {out_ellipse_path} successfully!")
