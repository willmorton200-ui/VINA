import cv2
import numpy as np

# Load mask and crop
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# 1. CYLINDER AXIS & SIDE GENERATORS
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

alpha = np.arctan(m_c) # -2.51 deg
v_axis = np.array([np.sin(alpha), np.cos(alpha)], dtype=np.float64) # along cylinder axis
v_axis /= np.linalg.norm(v_axis)

u_major = np.array([v_axis[1], -v_axis[0]], dtype=np.float64) # strictly perpendicular (90 deg)
u_major /= np.linalg.norm(u_major)

# 2. MATCH TOP AND BOTTOM BOUNDARIES DIRECTLY TO SAM MASK EXTENTS
y_indices, x_indices = np.where(mask > 127)
y_min_mask = float(np.min(y_indices)) # ~116 px (apex of top frowning arc over griffin)
y_max_mask = float(np.max(y_indices)) # ~1557 px (lowest extent of bottom smiling arc)

print(f"Mask extents: Y_top_apex = {y_min_mask:.1f}, Y_bot_apex = {y_max_mask:.1f}")

# Cross-section generator at any center C on axis:
def get_cross_section(C):
    denom_l = u_major[0] - m_l * u_major[1]
    t_L = (m_l * C[1] + c_l - C[0]) / denom_l
    D_left = C + t_L * u_major

    denom_r = u_major[0] - m_r * u_major[1]
    t_R = (m_r * C[1] + c_r - C[0]) / denom_r
    D_right = C + t_R * u_major

    a = np.linalg.norm(D_right - D_left) / 2.0
    C_mid = (D_left + D_right) / 2.0
    return C_mid, D_left, D_right, a

# Function to generate perspective semi-ellipse:
# signed_b > 0 => Smiling (apex dips downwards along v_axis by amount b)
# signed_b < 0 => Frowning (apex peaks upwards against v_axis by amount |b|)
def generate_perspective_semi_ellipse(C_mid, a, signed_b, N=120):
    thetas_front = np.linspace(-np.pi / 2.0, np.pi / 2.0, N)
    thetas_back  = np.linspace(np.pi / 2.0, 3 * np.pi / 2.0, N // 2)
    
    pts_front = []
    for th in thetas_front:
        # u along major axis (90 deg to cylinder axis)
        # v along cylinder axis = signed_b * cos(th)
        pt = C_mid + (np.sin(th) * a) * u_major + (signed_b * np.cos(th)) * v_axis
        pts_front.append(pt)
        
    pts_back = []
    for th in thetas_back:
        pt = C_mid + (np.sin(th) * a) * u_major + (signed_b * np.cos(th)) * v_axis
        pts_back.append(pt)
        
    return np.array(pts_front, dtype=np.float32), np.array(pts_back, dtype=np.float32)

# -------------------------------------------------------------
# 3. FIT PERSPECTIVE APERTURE FUNCTION b(y): FROWNING AT TOP -> SMILING AT BOTTOM
# -------------------------------------------------------------
# A. Top Rim (over griffin):
# Apex touches y_min_mask ~ 116 px.
# Top diameter C_top is at y ~ 155 px, so signed_b_top = - (155 - 116) = -39 px (FROWNING!)
y_top_center = 158.0
C_top_init = np.array([m_c * y_top_center + c_c, y_top_center], dtype=np.float64)
C_top, D_l_top, D_r_top, a_top = get_cross_section(C_top_init)
signed_b_top = -39.0 # Frowning: apex reaches y_min_mask = 119 px

# B. Text Row: "КРАСНОЕ СУХОЕ ВИНО" (at y ~ 1290 px)
# From our 3 text points: P_mid dips down by +27 px (SMILING!)
y_text_center = 1290.0
C_text_init = np.array([m_c * y_text_center + c_c, y_text_center], dtype=np.float64)
C_text, D_l_text, D_r_text, a_text = get_cross_section(C_text_init)
signed_b_text = +27.0 # Smiling

# C. Bottom Rim (at lowest extent of label):
# Diameter is at y ~ 1515 px, apex reaches y_max_mask ~ 1557 px => signed_b_bot = +(1557 - 1515) = +42 px (SMILING!)
y_bot_center = 1515.0
C_bot_init = np.array([m_c * y_bot_center + c_c, y_bot_center], dtype=np.float64)
C_bot, D_l_bot, D_r_bot, a_bot = get_cross_section(C_bot_init)
signed_b_bot = +42.0 # Smiling

# D. Horizon Level (where ellipse is edge-on / straight line):
# Linear transition: b(y) = signed_b_top + (y - y_top_center) / (y_bot_center - y_top_center) * (signed_b_bot - signed_b_top)
# b(y_horizon) = 0 => y_horizon ≈ y_top_center + 39 / (39 + 42) * (1515 - 158) ≈ 810 px (around 2021 / CABERNET)
y_horizon = y_top_center + (-signed_b_top) / (signed_b_bot - signed_b_top) * (y_bot_center - y_top_center)
print(f"Perspective Horizon Level: Y = {y_horizon:.1f} px (where ellipse is straight line)")

# -------------------------------------------------------------
# 4. RENDER ON MASK & COLOR IMAGE
# -------------------------------------------------------------
def render_perspective_geometry(canvas):
    vis = canvas.copy()
    
    # 1. Cylinder Axis (Red Dashed Line)
    p_axis_start = C_top - 80 * v_axis
    p_axis_end = C_bot + 80 * v_axis
    for s in range(0, int(np.linalg.norm(p_axis_end - p_axis_start)), 16):
        p1 = p_axis_start + s * v_axis
        p2 = p_axis_start + (s + 9) * v_axis
        cv2.line(vis, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), (0, 0, 255), 2, cv2.LINE_AA)
        
    cv2.putText(vis, "CYLINDER AXIS", (int(p_axis_start[0] + 15), int(p_axis_start[1] + 25)), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2, cv2.LINE_AA)

    # 2. Side Blue Tangents (matched to mask)
    eval_ys = np.linspace(80, 1600, 100)
    cv2.polylines(vis, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
    cv2.polylines(vis, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

    # 3. Draw Perspective Sections across height:
    # Top (Frown), Upper Text (Small Frown), Horizon (Straight), Lower Text (Smile), Bottom (Big Smile)
    sample_heights = [
        ("TOP RIM (FROWNING)", y_top_center, signed_b_top, (0, 255, 0)),
        ("ALMA VALLEY (SLIGHT FROWN)", 450.0, -18.0, (0, 220, 255)),
        ("HORIZON LEVEL (FLAT)", y_horizon, 0.0, (0, 255, 255)),
        ("TEXT ROW (SMILING)", y_text_center, signed_b_text, (0, 220, 255)),
        ("BOTTOM RIM (SMILING)", y_bot_center, signed_b_bot, (0, 255, 0))
    ]

    for label, y_h, b_signed, color in sample_heights:
        C_k_init = np.array([m_c * y_h + c_c, y_h], dtype=np.float64)
        C_k, D_l_k, D_r_k, a_k = get_cross_section(C_k_init)
        
        # Major axis line (90 deg to cylinder axis)
        p_maj_start = C_k - (a_k + 25) * u_major
        p_maj_end = C_k + (a_k + 25) * u_major
        cv2.line(vis, (int(p_maj_start[0]), int(p_maj_start[1])), (int(p_maj_end[0]), int(p_maj_end[1])), (0, 255, 0), 1, cv2.LINE_AA)
        
        # 90 deg symbol at key levels
        if "TOP" in label or "BOTTOM" in label:
            sq_sz = 14
            p_sq1 = C_k + sq_sz * u_major
            p_sq2 = p_sq1 + sq_sz * (-v_axis)
            p_sq3 = C_k + sq_sz * (-v_axis)
            cv2.polylines(vis, [np.array([C_k, p_sq1, p_sq2, p_sq3], dtype=np.int32)], False, (0, 255, 0), 2, cv2.LINE_AA)
            cv2.putText(vis, "90 deg", (int(C_k[0] - 70), int(C_k[1] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)

        # Generate Full Ellipse
        front_pts, back_pts = generate_perspective_semi_ellipse(C_k, a_k, b_signed)
        
        # Front semi-ellipse (Solid)
        cv2.polylines(vis, [front_pts.astype(np.int32)], False, color, 4 if ("TOP" in label or "BOTTOM" in label) else 2, lineType=cv2.LINE_AA)
        
        # Rear semi-ellipse (Dashed)
        for k in range(0, len(back_pts) - 1, 2):
            p1 = (int(back_pts[k, 0]), int(back_pts[k, 1]))
            p2 = (int(back_pts[k+1, 0]), int(back_pts[k+1, 1]))
            cv2.line(vis, p1, p2, (0, 180, 0), 1, cv2.LINE_AA)

    # 4. Highlight 3 points of text row on the smiling text ellipse
    p_left = np.array([131.5, 1317.0])
    p_mid = np.array([299.5, 1342.0])
    p_right = np.array([622.0, 1315.0])
    for pt in [p_left, p_mid, p_right]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 5, (0, 0, 255), -1, cv2.LINE_AA)

    return vis

vis_mask = render_perspective_geometry(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\gradual_smile_frown_mask.png", vis_mask)

vis_color = render_perspective_geometry(crop)
cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\gradual_smile_frown_color.png", vis_color)

print("Saved gradual_smile_frown_mask.png and gradual_smile_frown_color.png successfully!")
