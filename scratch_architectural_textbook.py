import cv2
import numpy as np

# Load mask and crop
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# -------------------------------------------------------------
# 1. CYLINDER AXIS & SIDE GENERATORS (Blue Tangents)
# -------------------------------------------------------------
# Left Generator:  x = m_l * y + c_l
# Right Generator: x = m_r * y + c_r
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64

# Central Axis of Cylinder: x = m_c * y + c_c
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

# Angle of cylinder axis relative to vertical (Y down)
# Vector along cylinder axis: v_axis = (m_c, 1) normalized
alpha = np.arctan(m_c) # ~ -2.51 deg
v_axis = np.array([np.sin(alpha), np.cos(alpha)], dtype=np.float64) # pointing along cylinder axis
v_axis /= np.linalg.norm(v_axis)

# Major axis of ellipse: MUST BE STRICTLY PERPENDICULAR (90 deg) to v_axis
# u_major = (cos(alpha), -sin(alpha))
u_major = np.array([v_axis[1], -v_axis[0]], dtype=np.float64)
u_major /= np.linalg.norm(u_major)

print(f"Cylinder Axis Angle alpha = {np.degrees(alpha):.3f} deg")
print(f"Axis vector:          v_axis  = [{v_axis[0]:.5f}, {v_axis[1]:.5f}]")
print(f"Ellipse Major vector: u_major = [{u_major[0]:.5f}, {u_major[1]:.5f}]")
print(f"Dot product (Strict 90 deg): {np.dot(v_axis, u_major):.8f}")

# -------------------------------------------------------------
# 2. EXACT CROSS-SECTION AT ANY POINT C ON CYLINDER AXIS
# -------------------------------------------------------------
# For any center C on axis:
# The line passing through C along u_major intersects Left Generator at D_left, Right at D_right
def get_cylinder_cross_section(C):
    # Intersect line C + t * u_major with Left generator x = m_l * y + c_l
    # C_x + t * u_major[0] = m_l * (C_y + t * u_major[1]) + c_l
    # t_L * (u_major[0] - m_l * u_major[1]) = m_l * C_y + c_l - C_x
    denom_l = u_major[0] - m_l * u_major[1]
    t_L = (m_l * C[1] + c_l - C[0]) / denom_l
    D_left = C + t_L * u_major

    denom_r = u_major[0] - m_r * u_major[1]
    t_R = (m_r * C[1] + c_r - C[0]) / denom_r
    D_right = C + t_R * u_major

    a = np.linalg.norm(D_right - D_left) / 2.0
    C_exact = (D_left + D_right) / 2.0
    return C_exact, D_left, D_right, a

# Parametric ellipse formula:
# P(theta) = C + (a * cos(theta)) * u_major + (b * sin(theta)) * v_axis
# theta in [0, pi]     -> Visible Front Half-Ellipse
# theta in [pi, 2*pi]  -> Hidden Rear Half-Ellipse (dashed)
def generate_full_ellipse(C, a, b, N=120):
    thetas_front = np.linspace(0, np.pi, N)
    thetas_back = np.linspace(np.pi, 2 * np.pi, N // 2)
    
    pts_front = []
    for th in thetas_front:
        pt = C + (a * np.cos(th)) * u_major + (b * np.sin(th)) * v_axis
        pts_front.append(pt)
        
    pts_back = []
    for th in thetas_back:
        pt = C + (a * np.cos(th)) * u_major + (b * np.sin(th)) * v_axis
        pts_back.append(pt)
        
    return np.array(pts_front, dtype=np.float32), np.array(pts_back, dtype=np.float32)

# -------------------------------------------------------------
# 3. FIT TEXT ROW: 3 KEY POINTS (КРАСНОЕ СУХОЕ ВИНО)
# -------------------------------------------------------------
# Text points in image coordinates
# P_left ('K'): (131.5, 1317.0), P_mid ('С/У'): (299.5, 1342.0), P_right ('О'): (622.0, 1315.0)
p_left = np.array([131.5, 1317.0], dtype=np.float64)
p_mid  = np.array([299.5, 1342.0], dtype=np.float64)
p_right = np.array([622.0, 1315.0], dtype=np.float64)

# Center of this text row on axis: C_text has Y coordinate matching P_left/P_right chord
y_text_axis = (p_left[1] + p_right[1]) / 2.0 - 25.0
C_text_init = np.array([m_c * y_text_axis + c_c, y_text_axis], dtype=np.float64)
C_text, D_l_text, D_r_text, a_text = get_cylinder_cross_section(C_text_init)

# The depth of the text ellipse: b = (P_mid - C_text) . v_axis
b_text = float(np.dot(p_mid - C_text, v_axis))
print(f"Text Ellipse: center=({C_text[0]:.1f}, {C_text[1]:.1f}), a={a_text:.1f} px, b={b_text:.1f} px")

# -------------------------------------------------------------
# 4. TOP AND BOTTOM SECTIONS OF CYLINDER
# -------------------------------------------------------------
# Top rim section (C_top)
y_top_axis = 135.0
C_top_init = np.array([m_c * y_top_axis + c_c, y_top_axis], dtype=np.float64)
C_top, D_l_top, D_r_top, a_top = get_cylinder_cross_section(C_top_init)
b_top = b_text * (a_top / a_text) # perspective scaling

# Bottom rim section (C_bot)
y_bot_axis = 1520.0
C_bot_init = np.array([m_c * y_bot_axis + c_c, y_bot_axis], dtype=np.float64)
C_bot, D_l_bot, D_r_bot, a_bot = get_cylinder_cross_section(C_bot_init)
b_bot = b_text * (a_bot / a_text)

# -------------------------------------------------------------
# 5. RENDER PURE ARCHITECTURAL DRAWING (Matching Рис. 4.54)
# -------------------------------------------------------------
def render_architectural_view(canvas):
    vis = canvas.copy()
    
    # 1. Draw CYLINDER AXIS ("ОСЬ БУТЫЛКИ" / "ОСЬ ЦИЛИНДРА") - Long Green Dashed Line
    p_axis_start = C_top - 90 * v_axis
    p_axis_end = C_bot + 90 * v_axis
    for s in range(0, int(np.linalg.norm(p_axis_end - p_axis_start)), 16):
        p1 = p_axis_start + s * v_axis
        p2 = p_axis_start + (s + 9) * v_axis
        cv2.line(vis, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (0, 255, 0), 2, cv2.LINE_AA)
        
    cv2.putText(vis, "CYLINDER AXIS", (int(p_axis_start[0] + 15), int(p_axis_start[1] + 30)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2, cv2.LINE_AA)

    # 2. Draw SIDE GENERATORS (Blue Tangents)
    eval_ys = np.linspace(80, 1600, 100)
    cv2.polylines(vis, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
    cv2.polylines(vis, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

    # 3. For each section (Top, Text, Bottom): Draw Major Axis (90 deg), 90 deg symbol, and Ellipse
    sections = [
        ("TOP SECTION", C_top, D_l_top, D_r_top, a_top, b_top),
        ("TEXT ROW SECTION", C_text, D_l_text, D_r_text, a_text, b_text),
        ("BOTTOM SECTION", C_bot, D_l_bot, D_r_bot, a_bot, b_bot)
    ]
    
    for label, C_k, D_l_k, D_r_k, a_k, b_k in sections:
        # A. Major Axis Line (strictly perpendicular to cylinder axis): extends past generators
        p_maj_start = C_k - (a_k + 35) * u_major
        p_maj_end = C_k + (a_k + 35) * u_major
        cv2.line(vis, (int(p_maj_start[0]), int(p_maj_start[1])), (int(p_maj_end[0]), int(p_maj_end[1])), (0, 255, 0), 2, cv2.LINE_AA)
        
        # B. 90-degree square right-angle mark at center C_k
        sq_sz = 16
        p_sq1 = C_k + sq_sz * u_major
        p_sq2 = p_sq1 + sq_sz * (-v_axis)
        p_sq3 = C_k + sq_sz * (-v_axis)
        cv2.polylines(vis, [np.array([C_k, p_sq1, p_sq2, p_sq3], dtype=np.int32)], False, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.circle(vis, (int(C_k[0] + sq_sz*0.5*u_major[0] - sq_sz*0.5*v_axis[0]), 
                         int(C_k[1] + sq_sz*0.5*u_major[1] - sq_sz*0.5*v_axis[1])), 2, (0, 255, 0), -1, cv2.LINE_AA)
        cv2.putText(vis, "90 deg", (int(C_k[0] - 80), int(C_k[1] - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)

        # C. Generate Full Ellipse
        front_pts, back_pts = generate_full_ellipse(C_k, a_k, b_k)
        
        # Front visible semi-ellipse (Solid thick Cyan/Green)
        cv2.polylines(vis, [front_pts.astype(np.int32)], False, (0, 255, 255) if "TEXT" in label else (0, 255, 0), 4, lineType=cv2.LINE_AA)
        
        # Rear hidden semi-ellipse (Dashed Green)
        for k in range(0, len(back_pts) - 1, 2):
            p1 = (int(back_pts[k, 0]), int(back_pts[k, 1]))
            p2 = (int(back_pts[k+1, 0]), int(back_pts[k+1, 1]))
            cv2.line(vis, p1, p2, (0, 200, 0), 2, cv2.LINE_AA)

    # 4. Highlight the 3 text points on the text row ellipse
    for pt in [p_left, p_mid, p_right]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 5, (0, 0, 255), -1, cv2.LINE_AA)

    return vis

# Render on mask
vis_mask = render_architectural_view(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\architectural_textbook_mask.png", vis_mask)

# Render on color crop
vis_color = render_architectural_view(crop)
cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\architectural_textbook_color.png", vis_color)

print("Saved architectural_textbook_mask.png and architectural_textbook_color.png successfully!")
