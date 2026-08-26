import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator

# Load mask and color image
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# 1. Cylinder Generators & Axis
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

y_min = 116.0
y_max = 1557.0

# 2. Extract Text Row (КРАСНОЕ СУХОЕ ВИНО or ALMA VALLEY)
# Let's find the 3 key points of the row "КРАСНОЕ СУХОЕ ВИНО" (y ~ 1240)
# P_left: bottom of 'K' (leftmost)
# P_mid:  bottom of 'C'/'У' in 'СУХОЕ' (middle, near central axis)
# P_right: bottom of 'О' in 'ВИНО' (rightmost)

# Binarize crop inside mask to accurately locate letter contours
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
binary_mask = cv2.bitwise_and(binary, mask)

num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary_mask)
row_chars = []
for i in range(1, num_labels):
    bx, by, bw, bh, area = stats[i]
    # Filter text row "КРАСНОЕ СУХОЕ ВИНО" (y in 1180..1300)
    if 1180 < by < 1300 and 8 < bh < 70 and 6 < bw < 70 and area > 30:
        row_chars.append({
            "cx": bx + bw / 2.0,
            "bot_y": by + bh,
            "bx": bx, "by": by, "bw": bw, "bh": bh
        })

row_chars.sort(key=lambda c: c["cx"])

# 3 POINTS: Leftmost, Middle (closest to axis x_c), Rightmost
p_left_char = row_chars[0]
p_right_char = row_chars[-1]

# Middle char: closest to cylinder axis x_c at this height
y_row_mid = (p_left_char["bot_y"] + p_right_char["bot_y"]) / 2.0
x_c_row = m_c * y_row_mid + c_c

p_mid_char = min(row_chars, key=lambda c: abs(c["cx"] - x_c_row))

p_left = np.array([p_left_char["cx"], p_left_char["bot_y"]], dtype=np.float32)
p_mid  = np.array([p_mid_char["cx"], p_mid_char["bot_y"]], dtype=np.float32)
p_right = np.array([p_right_char["cx"], p_right_char["bot_y"]], dtype=np.float32)

print(f"3 Key Points of Row:")
print(f"  P_left  (Leftmost char):  ({p_left[0]:.1f}, {p_left[1]:.1f})")
print(f"  P_mid   (Middle char):    ({p_mid[0]:.1f}, {p_mid[1]:.1f})")
print(f"  P_right (Rightmost char): ({p_right[0]:.1f}, {p_right[1]:.1f})")

# 3. ANALYTICAL ELLIPSE THROUGH THE 3 POINTS
# Cylinder half-width at this height:
x_l_row = m_l * y_row_mid + c_l
x_r_row = m_r * y_row_mid + c_r
a_row = (x_r_row - x_l_row) / 2.0
xc_row = (x_l_row + x_r_row) / 2.0

# Apex y0 is at middle point:
y0_row = p_mid[1]

# Calculate aperture b from left and right points:
dx_l = np.clip(abs(p_left[0] - xc_row) / a_row, 0.0, 0.98)
dx_r = np.clip(abs(p_right[0] - xc_row) / a_row, 0.0, 0.98)

sagitta_l = 1.0 - np.sqrt(1.0 - dx_l ** 2)
sagitta_r = 1.0 - np.sqrt(1.0 - dx_r ** 2)

b_from_l = (p_left[1] - y0_row) / max(sagitta_l, 1e-4) if (p_left[1] > y0_row) else (y0_row - p_left[1]) / max(sagitta_l, 1e-4)
b_from_r = (p_right[1] - y0_row) / max(sagitta_r, 1e-4) if (p_right[1] > y0_row) else (y0_row - p_right[1]) / max(sagitta_r, 1e-4)
b_row = max(abs(b_from_l + b_from_r) / 2.0, 15.0)

print(f"Text Ellipse parameters: xc={xc_row:.1f}, a={a_row:.1f}, b={b_row:.1f}, y0={y0_row:.1f}")

# 4. EXTRAPOLATE TO BOTTOM (TRUE BOTTOM GUIDE ARC)
x_l_bot = m_l * y_max + c_l
x_r_bot = m_r * y_max + c_r
a_bot = (x_r_bot - x_l_bot) / 2.0
xc_bot = (x_l_bot + x_r_bot) / 2.0
b_bot = b_row * (a_bot / a_row)

# 5. TOP ELLIPSE (UPPER RIM)
x_l_top = m_l * y_min + c_l
x_r_top = m_r * y_min + c_r
a_top = (x_r_top - x_l_top) / 2.0
xc_top = (x_l_top + x_r_top) / 2.0
b_top = b_row * (a_top / a_row)

# -------------------------------------------------------------
# 6. RENDER 3-POINT ELLIPSE VISUALIZATION
# -------------------------------------------------------------
vis = crop.copy()

# A. Central cylinder axis (Red dashed line)
for y_a in range(int(y_min - 30), int(y_max + 30), 14):
    x_a = int(m_c * y_a + c_c)
    cv2.line(vis, (x_a, y_a), (x_a, y_a + 7), (0, 0, 255), 2, cv2.LINE_AA)

# B. Blue side tangents
eval_ys = np.linspace(y_min - 30, y_max + 30, 100)
cv2.polylines(vis, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

# C. Draw Text Row Ellipse (Blue dashed ellipse passing through the 3 points)
thetas = np.linspace(-np.pi/2, np.pi/2, 100)
xs_text_ell = xc_row + a_row * np.sin(thetas)
ys_text_ell = (y0_row - b_row) + b_row * (1.0 - np.cos(thetas))
pts_text_ell = np.column_stack((xs_text_ell, ys_text_ell)).astype(np.int32)
cv2.polylines(vis, [pts_text_ell], False, (255, 180, 0), 3, lineType=cv2.LINE_AA)

# Draw the 3 KEY POINTS (Large circles with labels)
for pt, label in [(p_left, "P_left"), (p_mid, "P_mid (apex)"), (p_right, "P_right")]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 6, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 3, (0, 255, 255), -1, cv2.LINE_AA)
    cv2.putText(vis, label, (int(pt[0]) - 30, int(pt[1]) + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

# D. Draw Top Ellipse (Red)
xs_top_ell = xc_top + a_top * np.sin(thetas)
ys_top_ell = y_min + b_top * (1.0 - np.cos(thetas))
cv2.polylines(vis, [np.column_stack((xs_top_ell, ys_top_ell)).astype(np.int32)], False, (0, 0, 255), 4, lineType=cv2.LINE_AA)

# E. Draw True Bottom Guide Arc (Red, matching user's drawing)
xs_bot_ell = xc_bot + a_bot * np.sin(thetas)
ys_bot_ell = (y_max - b_bot) + b_bot * (1.0 - np.cos(thetas))
cv2.polylines(vis, [np.column_stack((xs_bot_ell, ys_bot_ell)).astype(np.int32)], False, (0, 0, 255), 4, lineType=cv2.LINE_AA)

out_3pt = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\three_point_ellipse_guide.png"
cv2.imwrite(out_3pt, vis)

# -------------------------------------------------------------
# 7. CONSTRUCT 3D MESH FROM 3-POINT ELLIPSE
# -------------------------------------------------------------
num_rows = 18
num_cols = 24
u_grid = np.zeros((num_rows, num_cols), dtype=np.float32)
v_grid = np.zeros((num_rows, num_cols), dtype=np.float32)

for i in range(num_rows):
    v = i / float(num_rows - 1)
    y_apex_v = (1.0 - v) * y_min + v * (y_max - b_bot)
    
    x_l_v = m_l * y_apex_v + c_l
    x_r_v = m_r * y_apex_v + c_r
    a_v = (x_r_v - x_l_v) / 2.0
    xc_v = (x_l_v + x_r_v) / 2.0
    b_v = (1.0 - v) * b_top + v * b_bot
    
    for j in range(num_cols):
        u = j / float(num_cols - 1)
        theta = -np.pi / 2.0 + u * np.pi
        
        x_pt = xc_v + a_v * np.sin(theta)
        y_pt = y_apex_v + b_v * (1.0 - np.cos(theta))
        
        u_grid[i, j] = x_pt
        v_grid[i, j] = y_pt

vis_mesh = crop.copy()
cv2.polylines(vis_mesh, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis_mesh, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

for i in range(num_rows):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 0, 255) if (i == 0 or i == num_rows - 1) else (0, 240, 255)
    thick = 3 if (i == 0 or i == num_rows - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, lineType=cv2.LINE_AA)

for j in range(num_cols):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    color = (255, 140, 0) if (j == 0 or j == num_cols - 1) else (0, 180, 255)
    thick = 3 if (j == 0 or j == num_cols - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, lineType=cv2.LINE_AA)

out_mesh = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\three_point_mesh.png"
cv2.imwrite(out_mesh, vis_mesh)

# 8. EXECUTE DEWARPING
dst_w = int(np.pi * ((a_top + a_bot)/2.0) * 0.95)
dst_h = int(y_max - y_min)

grid_y_flat, grid_x_flat = np.meshgrid(
    np.linspace(0, dst_h - 1, num_rows),
    np.linspace(0, dst_w - 1, num_cols),
    indexing='ij'
)

src_pts = np.column_stack((u_grid.ravel(), v_grid.ravel()))
dst_pts = np.column_stack((grid_x_flat.ravel(), grid_y_flat.ravel()))

rbf_u = RBFInterpolator(dst_pts, src_pts[:, 0], kernel='thin_plate_spline', smoothing=0.0)
rbf_v = RBFInterpolator(dst_pts, src_pts[:, 1], kernel='thin_plate_spline', smoothing=0.0)

out_ys, out_xs = np.meshgrid(np.arange(dst_h), np.arange(dst_w), indexing='ij')
dense_dst = np.column_stack((out_xs.ravel(), out_ys.ravel()))

map_x = rbf_u(dense_dst).reshape((dst_h, dst_w)).astype(np.float32)
map_y = rbf_v(dense_dst).reshape((dst_h, dst_w)).astype(np.float32)

dewarped = cv2.remap(crop, map_x, map_y, interpolation=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT)

out_dewarp = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\three_point_dewarped.png"
cv2.imwrite(out_dewarp, dewarped)

print("Saved three_point_ellipse_guide.png, three_point_mesh.png, and three_point_dewarped.png successfully!")
