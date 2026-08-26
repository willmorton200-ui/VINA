import cv2
import numpy as np
from scipy.interpolate import RBFInterpolator

# Load crop and mask
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# Side generators
m_l, c_l = -0.05181, 124.74
m_r, c_r = -0.03572, 701.64
m_c = (m_l + m_r) / 2.0
c_c = (c_l + c_r) / 2.0

# 4 Key corner points on generators
P_TL = np.array([118.3, 124.0])
P_TR = np.array([695.5, 171.0])
P_top_apex = np.array([408.1, 116.0])

P_BL = np.array([46.2, 1515.0])
P_BR = np.array([647.7, 1510.0])
P_bot_apex = np.array([345.1, 1556.0])

# Top sagitta: offset from mid chord to apex
sagitta_top = P_top_apex - (P_TL + P_TR) / 2.0  # points upwards (Frowns)
sagitta_bot = P_bot_apex - (P_BL + P_BR) / 2.0  # points downwards (Smiles)

# 3D Grid Generation using Keypoint-Anchored Transfinite Perspective Interpolation
num_rows = 18
num_cols = 24

u_grid = np.zeros((num_rows, num_cols), dtype=np.float32)
v_grid = np.zeros((num_rows, num_cols), dtype=np.float32)

for i in range(num_rows):
    v = i / float(num_rows - 1)  # 0.0 (top) to 1.0 (bottom)
    
    # Left and right keypoints at parameter v on generators
    P_left_v  = (1.0 - v) * P_TL + v * P_BL
    P_right_v = (1.0 - v) * P_TR + v * P_BR
    
    # Continuous sagitta transition from top frown to bottom smile
    sagitta_v = (1.0 - v) * sagitta_top + v * sagitta_bot
    
    for j in range(num_cols):
        u = j / float(num_cols - 1) # 0.0 (left) to 1.0 (right)
        
        # Exact perspective arc anchored strictly between P_left_v and P_right_v
        pt = (1.0 - u) * P_left_v + u * P_right_v + (4.0 * u * (1.0 - u)) * sagitta_v
        
        u_grid[i, j] = np.clip(pt[0], 0, w - 1)
        v_grid[i, j] = np.clip(pt[1], 0, h - 1)

# Render 3D Mesh on color crop
vis_mesh = crop.copy()

# Side generators
eval_ys = np.linspace(100, 1580, 100)
cv2.polylines(vis_mesh, [np.column_stack((m_l * eval_ys + c_l, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis_mesh, [np.column_stack((m_r * eval_ys + c_r, eval_ys)).astype(np.int32)], False, (255, 140, 0), 4, lineType=cv2.LINE_AA)

# Draw Horizontal Perspective Ring Arcs (Cyan / Green)
for i in range(num_rows):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 255, 0) if (i == 0 or i == num_rows - 1) else (0, 240, 255)
    thick = 3 if (i == 0 or i == num_rows - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, lineType=cv2.LINE_AA)

# Draw Vertical Generators (Light Cyan)
for j in range(num_cols):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    color = (255, 140, 0) if (j == 0 or j == num_cols - 1) else (0, 180, 255)
    thick = 3 if (j == 0 or j == num_cols - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, lineType=cv2.LINE_AA)

# Draw 4 corner Green Dots
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 8, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 6, (0, 255, 0), -1, cv2.LINE_AA)

out_mesh = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\keypoint_mesh_vanishing.png"
cv2.imwrite(out_mesh, vis_mesh)

# Perform TPS Dewarping
dst_w = int(max(np.linalg.norm(P_TR - P_TL), np.linalg.norm(P_BR - P_BL)))
dst_h = int(max(np.linalg.norm(P_BL - P_TL), np.linalg.norm(P_BR - P_TR)))

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

out_dewarp = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\keypoint_dewarped_vanishing.png"
cv2.imwrite(out_dewarp, dewarped)

print("Saved keypoint_mesh_vanishing.png and keypoint_dewarped_vanishing.png successfully!")
