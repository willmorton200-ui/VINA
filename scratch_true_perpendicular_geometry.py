import cv2
import numpy as np

# Load mask and crop
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# 1. BLUE SIDE TANGENTS (Left and Right Generators)
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64

# Central axis line: x_c(y) = m_c * y + c_c
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

# Unit vectors
theta = np.arctan(m_c)
cos_t = np.cos(theta)
sin_t = np.sin(theta)

# Axis direction pointing downwards: v_axis = (-sin_t, cos_t)
# Perpendicular major axis pointing rightwards: n_perp = (cos_t, sin_t)
# Verify dot product: (-sin_t)*cos_t + cos_t*sin_t == 0 (STRICT 90 DEGREES!)
v_axis = np.array([-sin_t, cos_t], dtype=np.float64)
n_perp = np.array([cos_t, sin_t], dtype=np.float64)

print(f"Cylinder Axis Angle: {np.degrees(theta):.2f} deg")
print(f"Dot product (Axis . Perpendicular) = {np.dot(v_axis, n_perp):.6f} (Strictly 90 deg!)")

# Function to get exact 90-degree cross-section diameter endpoints on the blue tangents
def get_cross_section(y_center):
    C = np.array([m_c * y_center + c_c, y_center], dtype=np.float64)
    
    # Intersect C + t * n_perp with Left tangent (x = m_l * y + c_l)
    t_L = (m_l * C[1] + c_l - C[0]) / (cos_t - m_l * sin_t)
    D_left = C + t_L * n_perp
    
    # Intersect C + t * n_perp with Right tangent (x = m_r * y + c_r)
    t_R = (m_r * C[1] + c_r - C[0]) / (cos_t - m_r * sin_t)
    D_right = C + t_R * n_perp
    
    # Midpoint and radius
    C_mid = (D_left + D_right) / 2.0
    a = np.linalg.norm(D_right - D_left) / 2.0
    return C_mid, D_left, D_right, a

# Function to generate pure semi-ellipse
# is_smile = True  => Smile  (tips at D_left, D_right; apex dips downwards along v_axis)
# is_smile = False => Frown  (tips at D_left, D_right; apex peaks upwards against v_axis)
def generate_semi_ellipse(C_mid, a, b, is_smile=True, N=120):
    thetas = np.linspace(-np.pi / 2.0, np.pi / 2.0, N)
    pts = []
    sign = 1.0 if is_smile else -1.0
    for th in thetas:
        u = np.sin(th) # from -1 to +1
        # Along perpendicular diameter: u * a * n_perp
        # Along cylinder axis: sign * b * cos(th) * v_axis  (cos(th) = sqrt(1 - u^2))
        pt = C_mid + (u * a) * n_perp + (sign * b * np.cos(th)) * v_axis
        pts.append(pt)
    return np.array(pts, dtype=np.float32)

# -------------------------------------------------------------
# 2. EXTRACT 3 KEY POINTS FROM COMPLETE ROW: "КРАСНОЕ СУХОЕ ВИНО"
# -------------------------------------------------------------
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
binary_mask = cv2.bitwise_and(binary, mask)

num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask)
row_chars = []
for i in range(1, num_labels):
    bx, by, bw, bh, area = stats[i]
    if 1200 < by < 1310 and 8 < bh < 70 and 6 < bw < 70 and area > 35:
        row_chars.append({
            "cx": bx + bw / 2.0,
            "bot_y": by + bh,
            "bx": bx, "by": by, "bw": bw, "bh": bh
        })

row_chars.sort(key=lambda c: c["cx"])

p_left_char = row_chars[0]
p_right_char = row_chars[-1]

y_row_approx = (p_left_char["bot_y"] + p_right_char["bot_y"]) / 2.0
C_row, D_l_row, D_r_row, a_row = get_cross_section(y_row_approx)

p_mid_char = min(row_chars, key=lambda c: abs(c["cx"] - C_row[0]))

p_left = np.array([float(p_left_char["cx"]), float(p_left_char["bot_y"])], dtype=np.float64)
p_mid  = np.array([float(p_mid_char["cx"]),  float(p_mid_char["bot_y"])],  dtype=np.float64)
p_right = np.array([float(p_right_char["cx"]), float(p_right_char["bot_y"])], dtype=np.float64)

# Calculate exact opening b from middle apex depth along axis:
# Middle point dips along axis: (p_mid - C_row) . v_axis = b
b_text = float(np.dot(p_mid - C_row, v_axis))
b_text = max(b_text, 25.0)

print(f"Text Row: a = {a_row:.1f} px, b = {b_text:.1f} px (Opening ratio = {b_text/a_row:.3f})")

# Generate Text Row Semi-Ellipse (Smiling)
text_semi_ellipse = generate_semi_ellipse(C_row, a_row, b_text, is_smile=True)

# -------------------------------------------------------------
# 3. TOP SEMI-ELLIPSE (Frowning at upper paper rim)
# -------------------------------------------------------------
y_top_center = 150.0
C_top, D_l_top, D_r_top, a_top = get_cross_section(y_top_center)
b_top = b_text * (a_top / a_row) * 0.8
top_semi_ellipse = generate_semi_ellipse(C_top, a_top, b_top, is_smile=False)

# -------------------------------------------------------------
# 4. BOTTOM GUIDE SEMI-ELLIPSE (Smiling at bottom)
# -------------------------------------------------------------
y_bot_center = 1505.0
C_bot, D_l_bot, D_r_bot, a_bot = get_cross_section(y_bot_center)
b_bot = b_text * (a_bot / a_row)
bot_semi_ellipse = generate_semi_ellipse(C_bot, a_bot, b_bot, is_smile=True)

# -------------------------------------------------------------
# 5. RENDER ARCHITECTURAL DRAWING WITH 90-DEGREE LABELS
# -------------------------------------------------------------
def render_architectural_drawing(img_canvas):
    vis = img_canvas.copy()
    
    # A. Central cylinder axis (Red dashed line)
    for y_a in range(80, 1600, 14):
        x_a = int(m_c * y_a + c_c)
        cv2.line(vis, (x_a, y_a), (x_a, y_a + 7), (0, 0, 255), 2, cv2.LINE_AA)
        
    # Axis label
    cv2.putText(vis, "CYLINDER AXIS", (int(m_c * 250 + c_c) + 15, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)

    # B. Blue side tangents (Generators)
    eval_ys = np.linspace(80, 1600, 100)
    cv2.polylines(vis, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
    cv2.polylines(vis, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

    # C. 90-DEGREE PERPENDICULAR DIAMETER LINES (Green dashed chords)
    for C_k, D_l_k, D_r_k in [(C_top, D_l_top, D_r_top), (C_row, D_l_row, D_r_row), (C_bot, D_l_bot, D_r_bot)]:
        p1 = (int(D_l_k[0] - 25 * cos_t), int(D_l_k[1] - 25 * sin_t))
        p2 = (int(D_r_k[0] + 25 * cos_t), int(D_r_k[1] + 25 * sin_t))
        # Draw green line
        cv2.line(vis, p1, p2, (0, 255, 0), 2, cv2.LINE_AA)
        # Draw 90 degree square symbol
        sq_size = 14
        sq_p1 = C_k + sq_size * n_perp
        sq_p2 = sq_p1 + sq_size * (-v_axis)
        sq_p3 = C_k + sq_size * (-v_axis)
        cv2.polylines(vis, [np.array([C_k, sq_p1, sq_p2, sq_p3], dtype=np.int32)], False, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(vis, "90 deg", (int(C_k[0] - 65), int(C_k[1] - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

    # D. Draw Semi-Ellipses (Thick Solid Curves)
    cv2.polylines(vis, [top_semi_ellipse.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA) # Green top
    cv2.polylines(vis, [text_semi_ellipse.astype(np.int32)], False, (0, 220, 255), 4, lineType=cv2.LINE_AA) # Cyan text
    cv2.polylines(vis, [bot_semi_ellipse.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA) # Green bottom

    # E. Draw 3 Text Key Points (Red circles with white borders)
    for pt, label in [(p_left, "P_left"), (p_mid, "P_mid (apex)"), (p_right, "P_right")]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 5, (0, 0, 255), -1, cv2.LINE_AA)

    return vis

# Render on binary mask
vis_mask = render_architectural_drawing(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
out_mask = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\true_90deg_perpendicular_mask.png"
cv2.imwrite(out_mask, vis_mask)

# Render on color photo
vis_color = render_architectural_drawing(crop)
out_color = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\true_90deg_perpendicular_color.png"
cv2.imwrite(out_color, vis_color)

print("Saved true_90deg_perpendicular_mask.png and true_90deg_perpendicular_color.png successfully!")
