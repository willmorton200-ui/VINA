import cv2
import numpy as np
from scipy.interpolate import interp1d, RBFInterpolator

# Load mask and crop
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")
h, w = mask.shape[:2]

# -------------------------------------------------------------
# 1. PRECISE CORNER IDENTIFICATION FROM MASK PROFILE
# -------------------------------------------------------------
# Scan row-by-row leftmost and rightmost mask pixels
y_indices, x_indices = np.where(mask > 127)
y_min = int(np.min(y_indices)) # 116
y_max = int(np.max(y_indices)) # 1556

# Find the leftmost and rightmost x for each y
left_x = np.zeros(h, dtype=np.int32)
right_x = np.zeros(h, dtype=np.int32)
for y in range(y_min, y_max + 1):
    xs = np.where(mask[y, :] > 127)[0]
    if len(xs) > 0:
        left_x[y] = xs[0]
        right_x[y] = xs[-1]

# The top curve is defined where mask exists between y_min and where left/right edges become vertical
# Let's find the exact top-left corner P_TL:
# In the top region (y between 116 and 180), find the leftmost x
top_y_range = range(y_min, y_min + 60)
tl_y = min(top_y_range, key=lambda y: left_x[y])
P_TL = np.array([float(left_x[tl_y]), float(tl_y)], dtype=np.float64) # (118.0, 124.0)

# Exact top-right corner P_TR:
tr_y = max(top_y_range, key=lambda y: right_x[y])
P_TR = np.array([float(right_x[tr_y]), float(tr_y)], dtype=np.float64) # (695.0, 171.0)

# Exact bottom-left corner P_BL:
bot_y_range = range(y_max - 60, y_max + 1)
bl_y = min(bot_y_range, key=lambda y: left_x[y])
P_BL = np.array([float(left_x[bl_y]), float(bl_y)], dtype=np.float64) # (48.0, 1515.0)

# Exact bottom-right corner P_BR:
br_y = max(bot_y_range, key=lambda y: right_x[y])
P_BR = np.array([float(right_x[br_y]), float(br_y)], dtype=np.float64) # (648.0, 1510.0)

print("Exact 4 Corners on SAM Mask boundary:")
print(f"  P_TL (Top-Left):     ({P_TL[0]:.1f}, {P_TL[1]:.1f})")
print(f"  P_TR (Top-Right):    ({P_TR[0]:.1f}, {P_TR[1]:.1f})")
print(f"  P_BL (Bottom-Left):  ({P_BL[0]:.1f}, {P_BL[1]:.1f})")
print(f"  P_BR (Bottom-Right): ({P_BR[0]:.1f}, {P_BR[1]:.1f})")

# -------------------------------------------------------------
# 2. EXACT TOP AND BOTTOM CONTOUR PROFILES
# -------------------------------------------------------------
# Scan top edge profile directly from mask between P_TL[0] and P_TR[0]
xs_top = np.linspace(P_TL[0], P_TR[0], 28)
ys_top = []
for x in xs_top:
    x_int = int(np.clip(x, 0, w - 1))
    ys = np.where(mask[:, x_int] > 127)[0]
    if len(ys) > 0:
        ys_top.append(float(np.min(ys)))
    else:
        ys_top.append(P_TL[1])
ys_top = np.array(ys_top, dtype=np.float32)

# Fit smooth quadratic curve for top boundary
poly_top = np.polyfit(xs_top, ys_top, deg=2)
T_x = xs_top
T_y = np.polyval(poly_top, T_x)
T_y[0] = P_TL[1]
T_y[-1] = P_TR[1]
T_curve = np.column_stack((T_x, T_y))

# Scan bottom edge profile directly from mask between P_BL[0] and P_BR[0]
xs_bot = np.linspace(P_BL[0], P_BR[0], 28)
ys_bot = []
for x in xs_bot:
    x_int = int(np.clip(x, 0, w - 1))
    ys = np.where(mask[:, x_int] > 127)[0]
    if len(ys) > 0:
        ys_bot.append(float(np.max(ys)))
    else:
        ys_bot.append(P_BL[1])
ys_bot = np.array(ys_bot, dtype=np.float32)

poly_bot = np.polyfit(xs_bot, ys_bot, deg=2)
B_x = xs_bot
B_y = np.polyval(poly_bot, B_x)
B_y[0] = P_BL[1]
B_y[-1] = P_BR[1]
B_curve = np.column_stack((B_x, B_y))

# -------------------------------------------------------------
# 3. UNIFORM 3D MESH GENERATION (TRANSFINITE COON'S PATCH)
# -------------------------------------------------------------
# Uniform step transition from Top curve T(u) to Bottom curve B(u)
N_rows = 22
N_cols = 28

u_vals = np.linspace(0.0, 1.0, N_cols)
v_vals = np.linspace(0.0, 1.0, N_rows)

L_curve = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
R_curve = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR

u_grid = np.zeros((N_rows, N_cols), dtype=np.float32)
v_grid = np.zeros((N_rows, N_cols), dtype=np.float32)

for i in range(N_rows):
    v = v_vals[i]
    for j in range(N_cols):
        u = u_vals[j]
        
        # Standard Bilinear Coon's Patch:
        # P(u,v) = (1-v)*T(u) + v*B(u) + (1-u)*L(v) + u*R(v) - [(1-u)(1-v)*P_TL + u(1-v)*P_TR + (1-u)v*P_BL + uv*P_BR]
        corner_blend = (1.0 - u) * (1.0 - v) * P_TL + u * (1.0 - v) * P_TR + (1.0 - u) * v * P_BL + u * v * P_BR
        pt = (1.0 - v) * T_curve[j] + v * B_curve[j] + (1.0 - u) * L_curve[i] + u * R_curve[i] - corner_blend
        
        u_grid[i, j] = pt[0]
        v_grid[i, j] = pt[1]

# -------------------------------------------------------------
# 4. RENDER ON MASK (Exact matching with user drawing)
# -------------------------------------------------------------
vis_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

# Blue Side Boundary Lines
cv2.line(vis_mask, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis_mask, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Green Top and Bottom Boundary Curves
cv2.polylines(vis_mask, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis_mask, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)

# Green Top Chord connecting P_TL and P_TR
cv2.line(vis_mask, (int(P_TL[0] - 25), int(P_TL[1] - 3)), (int(P_TR[0] + 25), int(P_TR[1] + 3)), (0, 255, 0), 1, cv2.LINE_AA)

# Central Axis (Red dashed line connecting midpoints)
p_top_mid = (P_TL + P_TR) / 2.0
p_bot_mid = (P_BL + P_BR) / 2.0
for s in range(0, int(np.linalg.norm(p_bot_mid - p_top_mid)), 14):
    v_s = s / float(np.linalg.norm(p_bot_mid - p_top_mid))
    pt_a = (1.0 - v_s) * p_top_mid + v_s * p_bot_mid
    pt_b = (1.0 - (v_s + 0.005)) * p_top_mid + (v_s + 0.005) * p_bot_mid
    cv2.line(vis_mask, (int(pt_a[0]), int(pt_a[1])), (int(pt_a[0]), int(pt_a[1] + 7)), (0, 0, 255), 2, cv2.LINE_AA)

# The 4 EXACT GREEN CORNER DOTS (Touching the mask exactly at corners!)
for pt, name in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
    cv2.circle(vis_mask, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mask, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

out_mask_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\exact_vector_corners_mask.png"
cv2.imwrite(out_mask_path, vis_mask)

# -------------------------------------------------------------
# 5. RENDER 3D MESH ON COLOR BOTTLE
# -------------------------------------------------------------
vis_mesh = crop.copy()

# Blue Side Boundary Lines
cv2.line(vis_mesh, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis_mesh, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

# Horizontal guide curves (Cyan, uniform step transition from Top curve to Bottom curve)
for i in range(N_rows):
    pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    color = (0, 255, 0) if (i == 0 or i == N_rows - 1) else (0, 240, 255)
    thick = 3 if (i == 0 or i == N_rows - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, lineType=cv2.LINE_AA)

# Vertical grid lines
for j in range(N_cols):
    pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    color = (255, 140, 0) if (j == 0 or j == N_cols - 1) else (0, 180, 255)
    thick = 3 if (j == 0 or j == N_cols - 1) else 1
    cv2.polylines(vis_mesh, [pts], False, color, thick, lineType=cv2.LINE_AA)

# 4 Corner Green Dots
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis_mesh, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

out_mesh_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\exact_vector_corners_mesh.png"
cv2.imwrite(out_mesh_path, vis_mesh)

# -------------------------------------------------------------
# 6. DEWARP USING UNIFORM TRANSITION MESH
# -------------------------------------------------------------
dst_w = int(max(np.linalg.norm(P_TR - P_TL), np.linalg.norm(P_BR - P_BL)))
dst_h = int(max(np.linalg.norm(P_BL - P_TL), np.linalg.norm(P_BR - P_TR)))

grid_y_flat, grid_x_flat = np.meshgrid(
    np.linspace(0, dst_h - 1, N_rows),
    np.linspace(0, dst_w - 1, N_cols),
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

out_dewarp_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\exact_vector_corners_dewarped.png"
cv2.imwrite(out_dewarp_path, dewarped)

print("Saved exact_vector_corners_mask.png, exact_vector_corners_mesh.png, and exact_vector_corners_dewarped.png successfully!")
