import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator

# Load crop and mask
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# Cylindrical Parameters
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

theta = np.arctan(m_c)
cos_t = np.cos(theta)
sin_t = np.sin(theta)

v_axis = np.array([-sin_t, cos_t], dtype=np.float64)
n_perp = np.array([cos_t, sin_t], dtype=np.float64)

# 3D Grid Parameters
num_rows = 18
num_cols = 24

u_grid = np.zeros((num_rows, num_cols), dtype=np.float32)
v_grid = np.zeros((num_rows, num_cols), dtype=np.float32)

y_top = 150.0
y_bot = 1505.0

# Generate pure 90-degree orthogonal cross-section mesh
for i in range(num_rows):
    v = i / float(num_rows - 1)  # 0.0 (top) to 1.0 (bottom)
    y_center = (1.0 - v) * y_top + v * y_bot
    
    # Calculate exact 90-degree diameter on cylinder
    C = np.array([m_c * y_center + c_c, y_center], dtype=np.float64)
    t_L = (m_l * C[1] + c_l - C[0]) / (cos_t - m_l * sin_t)
    t_R = (m_r * C[1] + c_r - C[0]) / (cos_t - m_r * sin_t)
    
    D_left = C + t_L * n_perp
    D_right = C + t_R * n_perp
    C_mid = (D_left + D_right) / 2.0
    a_v = np.linalg.norm(D_right - D_left) / 2.0
    
    # Perspective aperture b_v:
    # At top (v=0): b = 25.0 (frown sign = -1)
    # At bottom (v=1): b = 30.0 (smile sign = +1)
    if v < 0.20:
        sign = -1.0 * (1.0 - v/0.20)
        b_v = 22.0
    else:
        sign = 1.0
        b_v = 22.0 + (v - 0.20) * 10.0
        
    for j in range(num_cols):
        u = j / float(num_cols - 1)
        th = -np.pi / 2.0 + u * np.pi
        
        # Exact orthogonal point:
        pt = C_mid + (np.sin(th) * a_v) * n_perp + (sign * b_v * np.cos(th)) * v_axis
        u_grid[i, j] = np.clip(pt[0], 0, w - 1)
        v_grid[i, j] = np.clip(pt[1], 0, h - 1)

# Render 3D Mesh on color crop
vis_mesh = crop.copy()

# Side generators
eval_ys = np.linspace(y_top - 30, y_bot + 30, 100)
cv2.polylines(vis_mesh, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis_mesh, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

for i in range(num_rows):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 255, 0) if (i == 0 or i == num_rows - 1) else (0, 240, 255)
    thick = 3 if (i == 0 or i == num_rows - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, lineType=cv2.LINE_AA)

for j in range(num_cols):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    color = (255, 140, 0) if (j == 0 or j == num_cols - 1) else (0, 180, 255)
    thick = 3 if (j == 0 or j == num_cols - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, lineType=cv2.LINE_AA)

out_mesh = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\mesh_90deg_orthogonal.png"
cv2.imwrite(out_mesh, vis_mesh)

# TPS Dewarping
dst_w = int(np.pi * 299.0 * 0.95)
dst_h = int(y_bot - y_top)

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

out_dewarp = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\dewarped_90deg_orthogonal.png"
cv2.imwrite(out_dewarp, dewarped)

print("Saved mesh_90deg_orthogonal.png and dewarped_90deg_orthogonal.png successfully!")
