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

theta_axis = np.arctan(m_c)
cos_t = np.cos(theta_axis)
sin_t = np.sin(theta_axis)

y_top_apex = 116.0
y_bot_apex = 1557.0

# Text row aperture ratio: b / a ≈ 66.6 / 299.2 ≈ 0.222
k_aperture = 66.6 / 299.2

# 3D MESH GENERATION (Top frowns / middle to bottom smiles)
num_rows = 18
num_cols = 24

u_grid = np.zeros((num_rows, num_cols), dtype=np.float32)
v_grid = np.zeros((num_rows, num_cols), dtype=np.float32)

# Generate parametric cylinder surface
for i in range(num_rows):
    v = i / float(num_rows - 1)  # 0.0 (top) to 1.0 (bottom)
    
    y_apex_v = (1.0 - v) * y_top_apex + v * y_bot_apex
    C_v = np.array([m_c * y_apex_v + c_c, y_apex_v], dtype=np.float64)
    
    xl_v = m_l * y_apex_v + c_l
    xr_v = m_r * y_apex_v + c_r
    a_v = (xr_v - xl_v) / 2.0
    
    # In perspective: upper rim is near horizon / slightly frowning or transitioning to smile
    # Bottom rim smiles with full perspective aperture: b = k_aperture * a_v
    b_v = (1.0 - v) * (k_aperture * a_v * 0.5) + v * (k_aperture * a_v)
    
    # Transition from top frown to bottom smile
    sign_curve = (v - 0.25) / 0.75 if v < 0.25 else 1.0 # top 25% transitions to smile
    
    for j in range(num_cols):
        u = j / float(num_cols - 1)  # 0.0 (left) to 1.0 (right)
        theta = -np.pi / 2.0 + u * np.pi
        
        u_val = a_v * np.sin(theta)
        # For smiling (v >= 0.25): v_val = - b_v * (1 - cos(theta))  (tips go up)
        # For frowning (v < 0.25):  v_val = + b_v * (1 - cos(theta))  (tips go down)
        if v < 0.25:
            # Frowning at the very top
            v_val = (1.0 - v/0.25) * (b_v * (1.0 - np.cos(theta)))
        else:
            # Smiling from text lines down to the bottom
            v_val = - b_v * (1.0 - np.cos(theta))
            
        x_pt = C_v[0] + u_val * cos_t - v_val * sin_t
        y_pt = C_v[1] + u_val * sin_t + v_val * cos_t
        
        u_grid[i, j] = np.clip(x_pt, 0, w - 1)
        v_grid[i, j] = np.clip(y_pt, 0, h - 1)

# Render 3D Mesh on Color Bottle
vis_mesh = crop.copy()
eval_ys = np.linspace(y_top_apex - 30, y_bot_apex + 30, 100)
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

out_mesh_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\true_smile_mesh.png"
cv2.imwrite(out_mesh_path, vis_mesh)

# Perform TPS Dewarping
dst_w = int(np.pi * 299.2 * 0.95)
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

out_dewarp_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\true_smile_dewarped.png"
cv2.imwrite(out_dewarp_path, dewarped)

print("Saved true_smile_mesh.png and true_smile_dewarped.png successfully!")
