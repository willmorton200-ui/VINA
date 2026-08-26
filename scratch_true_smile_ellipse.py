import cv2
import numpy as np

# Load mask and crop
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# 1. CYLINDER GENERATORS & CENTRAL AXIS
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

# Cylinder tilt angle theta:
# The cylinder axis line is x = m_c * y + c_c.
# Vector along axis: (m_c, 1) normalized.
# Angle of axis with vertical: theta = arctan(m_c)
theta_axis = np.arctan(m_c)
cos_t = np.cos(theta_axis)
sin_t = np.sin(theta_axis)

print(f"Cylinder Axis: x = {m_c:.5f} * y + {c_c:.2f}, Tilt Angle = {np.degrees(theta_axis):.2f} deg")

# Perpendicular unit vector (Major axis of all cross-section ellipses):
# u_major = (cos_t, sin_t) -- strictly perpendicular to axis (-sin_t, cos_t)

# 2. LOCATE COMPLETE TEXT ROW: "КРАСНОЕ СУХОЕ ВИНО"
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
binary_mask = cv2.bitwise_and(binary, mask)

num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask)
row_chars = []
for i in range(1, num_labels):
    bx, by, bw, bh, area = stats[i]
    # Text row "КРАСНОЕ СУХОЕ ВИНО" (y in 1200..1310)
    if 1200 < by < 1310 and 8 < bh < 70 and 6 < bw < 70 and area > 35:
        row_chars.append({
            "cx": bx + bw / 2.0,
            "bot_y": by + bh,
            "bx": bx, "by": by, "bw": bw, "bh": bh
        })

row_chars.sort(key=lambda c: c["cx"])
print(f"Found {len(row_chars)} characters in text row 'КРАСНОЕ СУХОЕ ВИНО'")

# Extract 3 KEY POINTS from the complete row:
# P_left: bottom of 'K' in КРАСНОЕ
# P_right: bottom of 'О' in ВИНО
# P_mid: bottom of middle character (in СУХОЕ) closest to cylinder central axis
p_left_char = row_chars[0]
p_right_char = row_chars[-1]

y_row_approx = (p_left_char["bot_y"] + p_right_char["bot_y"]) / 2.0
xc_at_row = m_c * y_row_approx + c_c

p_mid_char = min(row_chars, key=lambda c: abs(c["cx"] - xc_at_row))

p_left = np.array([float(p_left_char["cx"]), float(p_left_char["bot_y"])], dtype=np.float64)
p_mid  = np.array([float(p_mid_char["cx"]),  float(p_mid_char["bot_y"])],  dtype=np.float64)
p_right = np.array([float(p_right_char["cx"]), float(p_right_char["bot_y"])], dtype=np.float64)

print(f"3 Key Points of Row:")
print(f"  P_left  ('K'):      ({p_left[0]:.1f}, {p_left[1]:.1f})")
print(f"  P_mid   ('С/У'):    ({p_mid[0]:.1f}, {p_mid[1]:.1f})")
print(f"  P_right ('О'):      ({p_right[0]:.1f}, {p_right[1]:.1f})")

# 3. CONSTRUCT PERSPECTIVE "SMILING" SEMI-ELLIPSE (улыбается: tips point UP, middle dips DOWN)
# Local coordinate frame aligned with cylinder axis and perpendicular major axis:
# Origin at cylinder axis at height y_mid: C = (x_c(y_mid), y_mid)
C_row = np.array([m_c * p_mid[1] + c_c, p_mid[1]], dtype=np.float64)

# Cylinder radius a_row at this height (half distance between left and right tangents along major axis)
xl_row = m_l * p_mid[1] + c_l
xr_row = m_r * p_mid[1] + c_r
a_row = (xr_row - xl_row) / 2.0

# Project P_left and P_right onto the rotated major axis (u) and axis (v):
def to_cylinder_frame(pt, C):
    dp = pt - C
    # u is along major axis (cos_t, sin_t)
    u = dp[0] * cos_t + dp[1] * sin_t
    # v is along cylinder axis (-sin_t, cos_t)
    v = -dp[0] * sin_t + dp[1] * cos_t
    return u, v

u_l, v_l = to_cylinder_frame(p_left, C_row)
u_r, v_r = to_cylinder_frame(p_right, C_row)
u_m, v_m = to_cylinder_frame(p_mid, C_row)

# The semi-ellipse "улыбается" (smile):
# In cylinder coordinates, the middle point is at the bottom (v = 0).
# As u moves away from center towards +/- a, the curve curves UPWARDS (v < 0 in downward-pointing axis frame):
# v(u) = - b * (1 - sqrt(1 - (u / a)^2))
# Thus: b = - v_L / (1 - sqrt(1 - (u_L / a)^2))

sagitta_l = 1.0 - np.sqrt(max(0.0, 1.0 - (u_l / a_row) ** 2))
sagitta_r = 1.0 - np.sqrt(max(0.0, 1.0 - (u_r / a_row) ** 2))

b_l = abs(v_l) / max(sagitta_l, 1e-4) if v_l < 0 else (p_mid[1] - p_left[1]) / max(sagitta_l, 1e-4)
b_r = abs(v_r) / max(sagitta_r, 1e-4) if v_r < 0 else (p_mid[1] - p_right[1]) / max(sagitta_r, 1e-4)
b_row = max((b_l + b_r) / 2.0, 20.0)

print(f"Row Ellipse: a = {a_row:.1f}, b = {b_row:.1f} (SMILING: tips go up by {b_row:.1f}px)")

# Function to generate a smiling semi-ellipse given cylinder center C = (xc, yc), radius a, and aperture b:
def generate_smiling_semi_ellipse(C, a, b, N=100):
    # Parametric angle theta from -pi/2 to pi/2
    thetas = np.linspace(-np.pi / 2.0, np.pi / 2.0, N)
    u_vals = a * np.sin(thetas)
    # Smiling curve: middle (theta=0) is at v=0, tips (theta=+/- pi/2) are UP at v = -b
    v_vals = - b * (1.0 - np.cos(thetas))
    
    # Rotate back to image coordinates (x, y)
    # [x, y]^T = C + u * [cos_t, sin_t]^T + v * [-sin_t, cos_t]^T
    xs = C[0] + u_vals * cos_t - v_vals * sin_t
    ys = C[1] + u_vals * sin_t + v_vals * cos_t
    return np.column_stack((xs, ys)).astype(np.int32)

# 4. EXTRAPOLATE TO TRUE BOTTOM GUIDE SEMI-ELLIPSE (УЛЫБАЕТСЯ ВНИЗУ)
y_bot_apex = 1557.0  # lowest extent of label paper
C_bot = np.array([m_c * y_bot_apex + c_c, y_bot_apex], dtype=np.float64)
xl_bot = m_l * y_bot_apex + c_l
xr_bot = m_r * y_bot_apex + c_r
a_bot = (xr_bot - xl_bot) / 2.0
b_bot = b_row * (a_bot / a_row)

bot_smile_ellipse = generate_smiling_semi_ellipse(C_bot, a_bot, b_bot)

# 5. TOP SEMI-ELLIPSE (ГРУСТИТ ВВЕРХУ: tips point DOWN, middle is at TOP)
y_top_apex = 116.0  # top apex above griffin
C_top = np.array([m_c * y_top_apex + c_c, y_top_apex], dtype=np.float64)
xl_top = m_l * y_top_apex + c_l
xr_top = m_r * y_top_apex + c_r
a_top = (xr_top - xl_top) / 2.0
b_top = b_row * (a_top / a_row) * 0.7  # top rim aperture

def generate_frowning_semi_ellipse(C, a, b, N=100):
    thetas = np.linspace(-np.pi / 2.0, np.pi / 2.0, N)
    u_vals = a * np.sin(thetas)
    # Frowning curve: middle (theta=0) is at v=0 (top), tips (theta=+/- pi/2) are DOWN at v = +b
    v_vals = b * (1.0 - np.cos(thetas))
    xs = C[0] + u_vals * cos_t - v_vals * sin_t
    ys = C[1] + u_vals * sin_t + v_vals * cos_t
    return np.column_stack((xs, ys)).astype(np.int32)

top_frown_ellipse = generate_frowning_semi_ellipse(C_top, a_top, b_top)

# 6. TEXT ROW SMILING SEMI-ELLIPSE
text_smile_ellipse = generate_smiling_semi_ellipse(C_row, a_row, b_row)

# -------------------------------------------------------------
# 7. RENDER ON MASK AND COLOR IMAGE
# -------------------------------------------------------------
vis_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

# Central axis (Red dashed line)
for y_a in range(int(y_top_apex - 30), int(y_bot_apex + 30), 14):
    x_a = int(m_c * y_a + c_c)
    cv2.line(vis_mask, (x_a, y_a), (x_a, y_a + 7), (0, 0, 255), 2, cv2.LINE_AA)

# Side Blue Tangents (strictly perpendicular to major axes)
eval_ys = np.linspace(y_top_apex - 30, y_bot_apex + 30, 100)
cv2.polylines(vis_mask, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 5, lineType=cv2.LINE_AA)
cv2.polylines(vis_mask, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 5, lineType=cv2.LINE_AA)

# Major axis line at text row (strictly perpendicular to axis)
p_major_l = C_row - a_row * np.array([cos_t, sin_t])
p_major_r = C_row + a_row * np.array([cos_t, sin_t])
cv2.line(vis_mask, (int(p_major_l[0]), int(p_major_l[1])), (int(p_major_r[0]), int(p_major_r[1])), (0, 255, 255), 1, cv2.LINE_AA)

# Draw Smiling Text Ellipse (Blue/Cyan)
cv2.polylines(vis_mask, [text_smile_ellipse], False, (255, 200, 0), 4, lineType=cv2.LINE_AA)

# Draw 3 Key Points of text row
for pt, label in [(p_left, "P_left"), (p_mid, "P_mid"), (p_right, "P_right")]:
    cv2.circle(vis_mask, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mask, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mask, (int(pt[0]), int(pt[1])), 3, (0, 255, 255), -1, cv2.LINE_AA)

# Draw Frowning Top Ellipse (Red)
cv2.polylines(vis_mask, [top_frown_ellipse], False, (0, 0, 255), 5, lineType=cv2.LINE_AA)

# Draw Smiling Bottom Ellipse (Red)
cv2.polylines(vis_mask, [bot_smile_ellipse], False, (0, 0, 255), 5, lineType=cv2.LINE_AA)

out_mask_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\true_smile_mask_geometry.png"
cv2.imwrite(out_mask_path, vis_mask)

# Render on Color Photo
vis_color = crop.copy()
for y_a in range(int(y_top_apex - 30), int(y_bot_apex + 30), 14):
    x_a = int(m_c * y_a + c_c)
    cv2.line(vis_color, (x_a, y_a), (x_a, y_a + 7), (0, 0, 255), 2, cv2.LINE_AA)

cv2.polylines(vis_color, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis_color, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
cv2.line(vis_color, (int(p_major_l[0]), int(p_major_l[1])), (int(p_major_r[0]), int(p_major_r[1])), (0, 255, 255), 1, cv2.LINE_AA)
cv2.polylines(vis_color, [text_smile_ellipse], False, (255, 200, 0), 4, lineType=cv2.LINE_AA)

for pt in [p_left, p_mid, p_right]:
    cv2.circle(vis_color, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_color, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_color, (int(pt[0]), int(pt[1])), 3, (0, 255, 255), -1, cv2.LINE_AA)

cv2.polylines(vis_color, [top_frown_ellipse], False, (0, 0, 255), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis_color, [bot_smile_ellipse], False, (0, 0, 255), 4, lineType=cv2.LINE_AA)

out_color_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\true_smile_color_geometry.png"
cv2.imwrite(out_color_path, vis_color)

print("Saved true_smile_mask_geometry.png and true_smile_color_geometry.png successfully!")
