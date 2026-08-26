import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator

# Load mask and crop
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# Cylindrical Parameters
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

y_top_apex = 116.0
y_bot_apex = 1557.0

# Top Ellipse
x_l_top = m_l * y_top_apex + c_l
x_r_top = m_r * y_top_apex + c_r
a_top = (x_r_top - x_l_top) / 2.0
xc_top = (x_l_top + x_r_top) / 2.0
b_top = 41.4  # from top mask profile

# Bottom Ellipse (from lowest text points)
x_l_bot = m_l * y_bot_apex + c_l
x_r_bot = m_r * y_bot_apex + c_r
a_bot = (x_r_bot - x_l_bot) / 2.0
xc_bot = (x_l_bot + x_r_bot) / 2.0
b_bot = 48.0  # proportional cylindrical opening at bottom

# Construct Cylindrical 3D Mesh using True Elliptical Cross-Sections
num_rows = 20
num_cols = 24

u_grid = np.zeros((num_rows, num_cols), dtype=np.float32)
v_grid = np.zeros((num_rows, num_cols), dtype=np.float32)

# Theta spans the visible front cylinder arc: theta in [-pi/2, pi/2]
for i in range(num_rows):
    v = i / float(num_rows - 1)  # 0.0 (top) to 1.0 (bottom)
    
    # Height of cylinder section
    y_apex_v = (1.0 - v) * y_top_apex + v * y_bot_apex
    
    # Section radius and center
    x_l_v = m_l * y_apex_v + c_l
    x_r_v = m_r * y_apex_v + c_r
    a_v = (x_r_v - x_l_v) / 2.0
    xc_v = (x_l_v + x_r_v) / 2.0
    
    # Minor axis b(v) interpolates from top to bottom
    b_v = (1.0 - v) * b_top + v * b_bot
    
    for j in range(num_cols):
        u = j / float(num_cols - 1)  # 0.0 (left) to 1.0 (right)
        
        # Elliptical parametric angle: theta from -pi/2 to pi/2
        theta = -np.pi / 2.0 + u * np.pi
        
        # Exact Ellipse equation on cylinder surface
        x_pt = xc_v + a_v * np.sin(theta)
        y_pt = y_apex_v + b_v * (1.0 - np.cos(theta))
        
        u_grid[i, j] = x_pt
        v_grid[i, j] = y_pt

# 1. RENDER MESH ON COLOR BOTTLE
vis_color = crop.copy()

# Side tangents
eval_ys = np.linspace(y_top_apex - 30, y_bot_apex + 30, 100)
cv2.polylines(vis_color, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis_color, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

# Draw Elliptical Horizontal Rings (Cyan)
for i in range(num_rows):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 0, 255) if (i == 0 or i == num_rows - 1) else (0, 240, 255)
    thick = 3 if (i == 0 or i == num_rows - 1) else 1
    cv2.polylines(vis_color, [pts], False, color, thick, lineType=cv2.LINE_AA)

# Draw Vertical Generators (Light Cyan)
for j in range(num_cols):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    color = (255, 140, 0) if (j == 0 or j == num_cols - 1) else (0, 180, 255)
    thick = 3 if (j == 0 or j == num_cols - 1) else 1
    cv2.polylines(vis_color, [pts], False, color, thick, lineType=cv2.LINE_AA)

# Highlight nodes
for i in range(0, num_rows, 2):
    for j in range(0, num_cols, 2):
        cv2.circle(vis_color, (int(u_grid[i, j]), int(v_grid[i, j])), 3, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_color, (int(u_grid[i, j]), int(v_grid[i, j])), 2, (0, 100, 255), -1, cv2.LINE_AA)

out_mesh_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\cylinder_mesh_from_ellipses.png"
cv2.imwrite(out_mesh_path, vis_color)

# 2. PERFORM TPS DEWARPING FROM TRUE CYLINDER ELLIPSES
# Flat unrolled cylinder dimensions: W = pi * a_avg, H = y_bot_apex - y_top_apex
a_avg = (a_top + a_bot) / 2.0
dst_w = int(np.pi * a_avg * 0.95)
dst_h = int(y_bot_apex - y_top_apex)

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

out_dewarped_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\cylinder_dewarped_from_ellipses.png"
cv2.imwrite(out_dewarped_path, dewarped)

print("Saved cylinder_mesh_from_ellipses.png and cylinder_dewarped_from_ellipses.png successfully!")
