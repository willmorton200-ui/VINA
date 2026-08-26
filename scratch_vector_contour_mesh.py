import cv2
import numpy as np

def generate_contour_and_mesh(mask_path, crop_path, prefix):
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    crop = cv2.imread(crop_path)
    h, w = mask.shape[:2]

    from pipeline.vectorizer import MaskVectorizer
    vec = MaskVectorizer()
    vm = vec.vectorize(mask)

    P_TL = vm.P_TL
    P_TR = vm.P_TR
    P_BL = vm.P_BL
    P_BR = vm.P_BR

    T_curve = vm.T_curve
    B_curve = vm.B_curve

    N_rows = 22
    N_cols = 28

    u_vals = np.linspace(0.0, 1.0, N_cols)
    v_vals = np.linspace(0.0, 1.0, N_rows)

    idx_orig = np.linspace(0.0, 1.0, len(T_curve))
    T_resamp = np.column_stack((
        np.interp(u_vals, idx_orig, T_curve[:, 0]),
        np.interp(u_vals, idx_orig, T_curve[:, 1])
    ))
    B_resamp = np.column_stack((
        np.interp(u_vals, idx_orig, B_curve[:, 0]),
        np.interp(u_vals, idx_orig, B_curve[:, 1])
    ))

    L_resamp = (1.0 - v_vals[:, None]) * P_TL + v_vals[:, None] * P_BL
    R_resamp = (1.0 - v_vals[:, None]) * P_TR + v_vals[:, None] * P_BR

    u_grid = np.zeros((N_rows, N_cols), dtype=np.float32)
    v_grid = np.zeros((N_rows, N_cols), dtype=np.float32)

    for i in range(N_rows):
        v = v_vals[i]
        for j in range(N_cols):
            u = u_vals[j]
            corner_blend = (1.0 - u) * (1.0 - v) * P_TL + u * (1.0 - v) * P_TR + (1.0 - u) * v * P_BL + u * v * P_BR
            pt = (1.0 - v) * T_resamp[j] + v * B_resamp[j] + (1.0 - u) * L_resamp[i] + u * R_resamp[i] - corner_blend
            u_grid[i, j] = pt[0]
            v_grid[i, j] = pt[1]

    # ---------------------------------------------------------
    # 1. RENDER VECTOR CONTOUR + 3D MESH ON MASK
    # ---------------------------------------------------------
    vis_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    # Draw 3D Mesh Grid on Mask
    for i in range(N_rows):
        pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
        color = (0, 255, 0) if (i == 0 or i == N_rows - 1) else (0, 240, 255)
        thick = 3 if (i == 0 or i == N_rows - 1) else 1
        cv2.polylines(vis_mask, [pts], False, color, thick, lineType=cv2.LINE_AA)

    for j in range(N_cols):
        pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
        color = (255, 140, 0) if (j == 0 or j == N_cols - 1) else (0, 180, 255)
        thick = 3 if (j == 0 or j == N_cols - 1) else 1
        cv2.polylines(vis_mask, [pts], False, color, thick, lineType=cv2.LINE_AA)

    # 4 Corner Green Dots
    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis_mask, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_mask, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

    out_mask = rf"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\{prefix}_mask_contour_mesh.png"
    cv2.imwrite(out_mask, vis_mask)

    # ---------------------------------------------------------
    # 2. RENDER VECTOR CONTOUR + 3D MESH ON COLOR BOTTLE (WITH GREENISH MASK TINT)
    # ---------------------------------------------------------
    vis_color = crop.copy()
    mask_bool = mask > 127
    green_layer = np.zeros_like(vis_color)
    green_layer[mask_bool] = [40, 225, 60]

    alpha = 0.30
    vis_color[mask_bool] = cv2.addWeighted(crop[mask_bool], 1.0 - alpha, green_layer[mask_bool], alpha, 0)

    # Draw 3D Mesh Grid on Color Image
    for i in range(N_rows):
        pts = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
        color = (0, 255, 0) if (i == 0 or i == N_rows - 1) else (0, 240, 255)
        thick = 3 if (i == 0 or i == N_rows - 1) else 1
        cv2.polylines(vis_color, [pts], False, color, thick, lineType=cv2.LINE_AA)

    for j in range(N_cols):
        pts = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
        color = (255, 140, 0) if (j == 0 or j == N_cols - 1) else (0, 180, 255)
        thick = 3 if (j == 0 or j == N_cols - 1) else 1
        cv2.polylines(vis_color, [pts], False, color, thick, lineType=cv2.LINE_AA)

    # 4 Corner Green Dots
    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis_color, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis_color, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

    out_color = rf"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\{prefix}_color_contour_mesh.png"
    cv2.imwrite(out_color, vis_color)
    print(f"Generated {prefix} contour & mesh images successfully!")

# Generate for Alma Valley
generate_contour_and_mesh(
    r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png",
    r"D:\VINA\outputs\test_pure_geometry\photo_2026-08-11_21-10-16\stage1_retinex.png",
    "alma_valley"
)

# Generate for Крепость Саркел (Bottle 07)
generate_contour_and_mesh(
    r"D:\VINA\outputs\test_bottle_21_10_07\photo_2026-08-11_21-10-07\stage1_mask.png",
    r"D:\VINA\outputs\test_bottle_21_10_07\photo_2026-08-11_21-10-07\stage1_retinex.png",
    "sarkel"
)
