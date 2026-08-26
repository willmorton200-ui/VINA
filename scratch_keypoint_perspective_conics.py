import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator

# Load mask and crop
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# 1. BLUE SIDE GENERATORS (Left and Right Tangents of the mask)
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64

# Central axis
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

# -------------------------------------------------------------
# 2. KEY POINTS OF THE MASK (ЗЕЛЕНЫЕ ТОЧКИ НАЧАЛ ЭЛЛИПСОВ)
# -------------------------------------------------------------
# Find exact contour and boundary extents
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea).squeeze()

y_min_mask = float(np.min(cnt[:, 1])) # ~116 px
y_max_mask = float(np.max(cnt[:, 1])) # ~1557 px

# TOP KEY POINTS:
# P_TL: Intersection of top cut with Left Generator (Top-Left green dot)
# P_TR: Intersection of top cut with Right Generator (Top-Right green dot)
# P_top_apex: Highest point on the top cut above the griffin
y_tl = float(np.min(cnt[cnt[:, 0] < 150, 1])) # ~135 px
x_tl = m_l * y_tl + c_l
P_TL = np.array([x_tl, y_tl], dtype=np.float64)

y_tr = float(np.min(cnt[cnt[:, 0] > 650, 1])) # ~190 px
x_tr = m_r * y_tr + c_r
P_TR = np.array([x_tr, y_tr], dtype=np.float64)

# Top apex on the central axis:
top_apex_pts = cnt[(cnt[:, 0] > 350) & (cnt[:, 0] < 470)]
P_top_apex = np.array([m_c * y_min_mask + c_c, y_min_mask], dtype=np.float64)

print(f"Top Key Points:")
print(f"  P_TL (Top-Left Green Dot):  ({P_TL[0]:.1f}, {P_TL[1]:.1f})")
print(f"  P_top_apex (Griffin Apex):  ({P_top_apex[0]:.1f}, {P_top_apex[1]:.1f})")
print(f"  P_TR (Top-Right Green Dot): ({P_TR[0]:.1f}, {P_TR[1]:.1f})")

# BOTTOM KEY POINTS:
# P_BL: Intersection of bottom curve with Left Generator (Bottom-Left green dot)
# P_BR: Intersection of bottom curve with Right Generator (Bottom-Right green dot)
y_bl = 1515.0
x_bl = m_l * y_bl + c_l
P_BL = np.array([x_bl, y_bl], dtype=np.float64)

y_br = 1510.0
x_br = m_r * y_br + c_r
P_BR = np.array([x_br, y_br], dtype=np.float64)

# Bottom apex (lowest extent of the smiling arc):
P_bot_apex = np.array([m_c * y_max_mask + c_c, y_max_mask], dtype=np.float64)

print(f"Bottom Key Points:")
print(f"  P_BL (Bottom-Left Green Dot):  ({P_BL[0]:.1f}, {P_BL[1]:.1f})")
print(f"  P_bot_apex (Bottom Apex):      ({P_bot_apex[0]:.1f}, {P_bot_apex[1]:.1f})")
print(f"  P_BR (Bottom-Right Green Dot): ({P_BR[0]:.1f}, {P_BR[1]:.1f})")

# -------------------------------------------------------------
# 3. TEXT ROW 3 KEY POINTS (КРАСНОЕ СУХОЕ ВИНО)
# -------------------------------------------------------------
# 3 points of text row: P_text_L, P_text_mid, P_text_R
P_text_L = np.array([131.5, 1317.0], dtype=np.float64) # 'K'
P_text_M = np.array([299.5, 1342.0], dtype=np.float64) # 'С/У' (mid apex)
P_text_R = np.array([622.0, 1315.0], dtype=np.float64) # 'О'

# Extrapolate text row to intersect left and right blue generators:
# The chord P_text_L -> P_text_R defines the perspective baseline tilt towards vanishing point
dir_text = (P_text_R - P_text_L) / np.linalg.norm(P_text_R - P_text_L)

# Intersect with left generator x = m_l * y + c_l:
# P_text_L_x + t * dir_x = m_l * (P_text_L_y + t * dir_y) + c_l
t_text_l = (m_l * P_text_L[1] + c_l - P_text_L[0]) / (dir_text[0] - m_l * dir_text[1])
P_text_edge_L = P_text_L + t_text_l * dir_text

t_text_r = (m_r * P_text_R[1] + c_r - P_text_R[0]) / (dir_text[0] - m_r * dir_text[1])
P_text_edge_R = P_text_R + t_text_r * dir_text

print(f"Text Row Key Points on Generators:")
print(f"  P_text_edge_L: ({P_text_edge_L[0]:.1f}, {P_text_edge_L[1]:.1f})")
print(f"  P_text_mid:    ({P_text_M[0]:.1f}, {P_text_M[1]:.1f})")
print(f"  P_text_edge_R: ({P_text_edge_R[0]:.1f}, {P_text_edge_R[1]:.1f})")

# -------------------------------------------------------------
# 4. PERSPECTIVE 3-POINT ELLIPTICAL ARC FORMULA
# -------------------------------------------------------------
# Given left endpoint P1 (on left generator), right endpoint P3 (on right generator), and apex P2:
# In 2D perspective, the curve is:
# P(u) = (1 - u) * P1 + u * P3 + 4 * u * (1 - u) * (P2 - (P1 + P3)/2)
# for u in [0, 1].
# Note:
#  u = 0   => P1 (exact Left Green Dot!)
#  u = 1   => P3 (exact Right Green Dot!)
#  u = 0.5 => P2 (exact Middle Apex!)
#  The chord P1-P3 is tilted directly towards the perspective vanishing point on the horizon!

def generate_perspective_arc(P1, P2, P3, N=120):
    u_vals = np.linspace(0.0, 1.0, N)
    mid_chord = (P1 + P3) / 2.0
    sagitta = P2 - mid_chord # vector offset at apex
    
    pts = []
    for u in u_vals:
        pt = (1.0 - u) * P1 + u * P3 + (4.0 * u * (1.0 - u)) * sagitta
        pts.append(pt)
    return np.array(pts, dtype=np.float32)

top_arc_curve  = generate_perspective_arc(P_TL, P_top_apex, P_TR)
text_arc_curve = generate_perspective_arc(P_text_edge_L, P_text_M, P_text_edge_R)
bot_arc_curve  = generate_perspective_arc(P_BL, P_bot_apex, P_BR)

# -------------------------------------------------------------
# 5. RENDER ON MASK & COLOR IMAGE
# -------------------------------------------------------------
def render_perspective_keypoints(canvas):
    vis = canvas.copy()
    
    # 1. Cylinder Axis (Red Dashed Line)
    for y_a in range(80, 1600, 14):
        x_a = int(m_c * y_a + c_c)
        cv2.line(vis, (x_a, y_a), (x_a, y_a + 7), (0, 0, 255), 2, cv2.LINE_AA)
        
    cv2.putText(vis, "CYLINDER AXIS", (int(m_c * 260 + c_c) + 15, 260), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 255), 2, cv2.LINE_AA)

    # 2. Side Blue Generators (Thick Blue Lines)
    eval_ys = np.linspace(80, 1600, 100)
    cv2.polylines(vis, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
    cv2.polylines(vis, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

    # 3. Perspective Vanishing Chords (Green dashed lines connecting left & right green dots)
    for P1, P3 in [(P_TL, P_TR), (P_text_edge_L, P_text_edge_R), (P_BL, P_BR)]:
        # Extend slightly past generators
        dir_chord = (P3 - P1) / np.linalg.norm(P3 - P1)
        p_start = P1 - 30 * dir_chord
        p_end = P3 + 30 * dir_chord
        cv2.line(vis, (int(p_start[0]), int(p_start[1])), (int(p_end[0]), int(p_end[1])), (0, 255, 0), 2, cv2.LINE_AA)

    # 4. Draw Perspective Semi-Ellipses (Thick Solid Curves)
    cv2.polylines(vis, [top_arc_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)  # Top (Frowns over griffin)
    cv2.polylines(vis, [text_arc_curve.astype(np.int32)], False, (0, 220, 255), 4, lineType=cv2.LINE_AA) # Text (Smiles)
    cv2.polylines(vis, [bot_arc_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)  # Bottom (Smiles)

    # 5. Draw the 4 GREEN KEY DOTS at intersections with blue generators
    for pt, label in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA) # Large Green Dot

    # 6. Draw the 3 RED TEXT POINTS
    for pt in [P_text_L, P_text_M, P_text_R]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 5, (0, 0, 255), -1, cv2.LINE_AA)

    return vis

vis_mask = render_perspective_keypoints(cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR))
cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\keypoint_perspective_mask.png", vis_mask)

vis_color = render_perspective_keypoints(crop)
cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\keypoint_perspective_color.png", vis_color)

print("Saved keypoint_perspective_mask.png and keypoint_perspective_color.png successfully!")
