import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator

# 1. Load mask and color image
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\vector_stage1_retinex.png")

h, w = mask.shape[:2]

# 2. Geometric Vector Model
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64
top_poly = np.array([4.93837395e-04, -3.04515942e-01, 1.61079294e+02])

# Extents
y_min = 116.0
y_max = 1557.0

x_tl = m_l * (y_min + 15) + c_l
x_tr = m_r * (y_min + 15) + c_r
x_bl = m_l * (y_max - 15) + c_l
x_br = m_r * (y_max - 15) + c_r

curv_top = top_poly[0]
cx_bot = (x_bl + x_br) / 2.0
bot_poly = np.array([-curv_top * 0.9, 2.0 * curv_top * 0.9 * cx_bot, y_max - (curv_top * 0.9) * (cx_bot ** 2)])

p_tl = np.array([x_tl, np.polyval(top_poly, x_tl)], dtype=np.float32)
p_tr = np.array([x_tr, np.polyval(top_poly, x_tr)], dtype=np.float32)
p_br = np.array([x_br, np.polyval(bot_poly, x_br)], dtype=np.float32)
p_bl = np.array([x_bl, np.polyval(bot_poly, x_bl)], dtype=np.float32)

# -------------------------------------------------------------
# 3. CONSTRUCT 3D COON'S PATCH GRID
# -------------------------------------------------------------
num_rows = 18
num_cols = 24

u_grid = np.zeros((num_rows, num_cols), dtype=np.float32)
v_grid = np.zeros((num_rows, num_cols), dtype=np.float32)

# Normalized coordinates (u, v) in [0, 1] x [0, 1]
for i in range(num_rows):
    v = i / float(num_rows - 1)  # 0.0 (top) to 1.0 (bottom)
    
    # Left and right boundary points at parameter v
    y_l = (1.0 - v) * p_tl[1] + v * p_bl[1]
    x_l = m_l * y_l + c_l
    pt_L = np.array([x_l, y_l], dtype=np.float32)
    
    y_r = (1.0 - v) * p_tr[1] + v * p_br[1]
    x_r = m_r * y_r + c_r
    pt_R = np.array([x_r, y_r], dtype=np.float32)
    
    for j in range(num_cols):
        u = j / float(num_cols - 1)  # 0.0 (left) to 1.0 (right)
        
        # Top and bottom boundary points at parameter u
        x_t = (1.0 - u) * p_tl[0] + u * p_tr[0]
        y_t = np.polyval(top_poly, x_t)
        pt_T = np.array([x_t, y_t], dtype=np.float32)
        
        x_b = (1.0 - u) * p_bl[0] + u * p_br[0]
        y_b = np.polyval(bot_poly, x_b)
        pt_B = np.array([x_b, y_b], dtype=np.float32)
        
        # Bilinear corner correction
        pt_corners = (1.0 - u) * (1.0 - v) * p_tl + \
                     u * (1.0 - v) * p_tr + \
                     (1.0 - u) * v * p_bl + \
                     u * v * p_br
                     
        # Transfinite Coon's Interpolation formula
        pt_S = (1.0 - v) * pt_T + v * pt_B + (1.0 - u) * pt_L + u * pt_R - pt_corners
        
        u_grid[i, j] = pt_S[0]
        v_grid[i, j] = pt_S[1]

# -------------------------------------------------------------
# 4. RENDER 3D MESH ON BINARY MASK
# -------------------------------------------------------------
vis_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

# Blue side tangents (thick)
eval_ys_ext = np.linspace(y_min - 30, y_max + 30, 100)
left_line_ext = np.column_stack((m_l * eval_ys_ext + c_l, eval_ys_ext)).astype(np.int32)
right_line_ext = np.column_stack((m_r * eval_ys_ext + c_r, eval_ys_ext)).astype(np.int32)
cv2.polylines(vis_mask, [left_line_ext], False, (255, 140, 0), 5, lineType=cv2.LINE_AA)
cv2.polylines(vis_mask, [right_line_ext], False, (255, 140, 0), 5, lineType=cv2.LINE_AA)

# Draw Horizontal Mesh Iso-Curves (Cyan/Yellow)
for i in range(num_rows):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 0, 255) if (i == 0 or i == num_rows - 1) else (0, 240, 255)
    thick = 4 if (i == 0 or i == num_rows - 1) else 1
    cv2.polylines(vis_mask, [pts], False, color, thick, lineType=cv2.LINE_AA)

# Draw Vertical Mesh Iso-Generators (Light Cyan)
for j in range(num_cols):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    color = (255, 140, 0) if (j == 0 or j == num_cols - 1) else (0, 180, 255)
    thick = 4 if (j == 0 or j == num_cols - 1) else 1
    cv2.polylines(vis_mask, [pts], False, color, thick, lineType=cv2.LINE_AA)

# Highlight Mesh Control Nodes (Dots)
for i in range(num_rows):
    for j in range(num_cols):
        cv2.circle(vis_mask, (int(u_grid[i, j]), int(v_grid[i, j])), 2, (0, 80, 255), -1, cv2.LINE_AA)

# Save mask mesh visualization
out_mask_mesh = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\mesh_on_binary_mask.png"
cv2.imwrite(out_mask_mesh, vis_mask)

# -------------------------------------------------------------
# 5. RENDER 3D MESH ON COLOR BOTTLE PHOTO
# -------------------------------------------------------------
vis_color = crop.copy()
cv2.polylines(vis_color, [left_line_ext], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis_color, [right_line_ext], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

for i in range(num_rows):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 0, 255) if (i == 0 or i == num_rows - 1) else (0, 240, 255)
    thick = 3 if (i == 0 or i == num_rows - 1) else 1
    cv2.polylines(vis_color, [pts], False, color, thick, lineType=cv2.LINE_AA)

for j in range(num_cols):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    color = (255, 140, 0) if (j == 0 or j == num_cols - 1) else (0, 180, 255)
    thick = 3 if (j == 0 or j == num_cols - 1) else 1
    cv2.polylines(vis_color, [pts], False, color, thick, lineType=cv2.LINE_AA)

for i in range(0, num_rows, 2):
    for j in range(0, num_cols, 2):
        cv2.circle(vis_color, (int(u_grid[i, j]), int(v_grid[i, j])), 3, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_color, (int(u_grid[i, j]), int(v_grid[i, j])), 2, (0, 100, 255), -1, cv2.LINE_AA)

out_color_mesh = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\mesh_on_color_bottle.png"
cv2.imwrite(out_color_mesh, vis_color)

# -------------------------------------------------------------
# 6. EXECUTE PERFECT TPS DEWARPING FROM THIS MESH
# -------------------------------------------------------------
# Destination coordinates (flat rectangle)
dst_w = int(max(np.linalg.norm(p_tr - p_tl), np.linalg.norm(p_br - p_bl)))
dst_h = int(max(np.linalg.norm(p_bl - p_tl), np.linalg.norm(p_br - p_tr)))

grid_y_flat, grid_x_flat = np.meshgrid(
    np.linspace(0, dst_h - 1, num_rows),
    np.linspace(0, dst_w - 1, num_cols),
    indexing='ij'
)

src_pts = np.column_stack((u_grid.ravel(), v_grid.ravel()))
dst_pts = np.column_stack((grid_x_flat.ravel(), grid_y_flat.ravel()))

# Fit TPS backward mapping
rbf_u = RBFInterpolator(dst_pts, src_pts[:, 0], kernel='thin_plate_spline', smoothing=0.0)
rbf_v = RBFInterpolator(dst_pts, src_pts[:, 1], kernel='thin_plate_spline', smoothing=0.0)

# Dense evaluation on output grid
out_ys, out_xs = np.meshgrid(np.arange(dst_h), np.arange(dst_w), indexing='ij')
dense_dst = np.column_stack((out_xs.ravel(), out_ys.ravel()))

map_x = rbf_u(dense_dst).reshape((dst_h, dst_w)).astype(np.float32)
map_y = rbf_v(dense_dst).reshape((dst_h, dst_w)).astype(np.float32)

dewarped = cv2.remap(crop, map_x, map_y, interpolation=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT)

out_dewarped = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\perfect_mesh_dewarped.png"
cv2.imwrite(out_dewarped, dewarped)

print("Saved mesh_on_binary_mask.png, mesh_on_color_bottle.png, and perfect_mesh_dewarped.png successfully!")
