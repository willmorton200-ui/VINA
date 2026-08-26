import cv2
import numpy as np

def extract_exact_mask_corners(mask: np.ndarray):
    """
    Robustly extracts the 4 true physical corner vertices (P_TL, P_TR, P_BL, P_BR)
    by finding where the lateral side boundaries (nearly straight lines)
    meet the top and bottom curved boundaries of the SAM mask.
    """
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY) if mask.shape[2] == 3 else mask[:, :, 0]

    h, w = mask.shape[:2]

    # 1. Clean mask to single largest component
    binary = np.uint8(mask > 127)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels > 2:
        largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        clean_mask = np.zeros((h, w), dtype=np.uint8)
        clean_mask[labels == largest_label] = 255
        mask = clean_mask

    # 2. Extract Left and Right Profiles
    y_indices, x_indices = np.where(mask > 127)
    y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
    H_span = y_max - y_min

    left_pts = []
    right_pts = []
    for y in range(y_min, y_max + 1):
        xs = np.where(mask[y, :] > 127)[0]
        if len(xs) > 0:
            left_pts.append((float(xs[0]), float(y)))
            right_pts.append((float(xs[-1]), float(y)))

    left_pts = np.array(left_pts)
    right_pts = np.array(right_pts)

    # 3. Fit Straight Lateral Generator Lines through middle 60% of vertical span
    mid_start = int(len(left_pts) * 0.20)
    mid_end = int(len(left_pts) * 0.80)

    # Fit line x = m*y + c
    poly_L = np.polyfit(left_pts[mid_start:mid_end, 1], left_pts[mid_start:mid_end, 0], deg=1) # [m_L, c_L]
    poly_R = np.polyfit(right_pts[mid_start:mid_end, 1], right_pts[mid_start:mid_end, 0], deg=1) # [m_R, c_R]

    # 4. Find Top-Left and Bottom-Left corners:
    # Deviation of actual left_x from the fitted side line
    # Near the middle, deviation is ~0.
    # At top arch and bottom arch, deviation exceeds threshold as boundary curves away towards center!
    dev_L = left_pts[:, 0] - (poly_L[0] * left_pts[:, 1] + poly_L[1])
    
    # Top-Left: highest y (lowest row index) where dev_L is still small (< 8px)
    mid_idx = len(left_pts) // 2
    tl_idx = 0
    for idx in range(mid_idx, -1, -1):
        if dev_L[idx] > 6.0:
            tl_idx = idx + 1
            break
    tl_idx = min(tl_idx, mid_idx)
    P_TL = left_pts[tl_idx].copy()

    # Bottom-Left: lowest y (highest row index) where dev_L is still small (< 8px)
    bl_idx = len(left_pts) - 1
    for idx in range(mid_idx, len(left_pts)):
        if dev_L[idx] > 6.0:
            bl_idx = idx - 1
            break
    bl_idx = max(bl_idx, mid_idx)
    P_BL = left_pts[bl_idx].copy()

    # 5. Find Top-Right and Bottom-Right corners:
    # For right side, boundary curves inwards (dev_R = fitted - actual becomes > 0)
    dev_R = (poly_R[0] * right_pts[:, 1] + poly_R[1]) - right_pts[:, 0]
    
    tr_idx = 0
    for idx in range(mid_idx, -1, -1):
        if dev_R[idx] > 6.0:
            tr_idx = idx + 1
            break
    tr_idx = min(tr_idx, mid_idx)
    P_TR = right_pts[tr_idx].copy()

    br_idx = len(right_pts) - 1
    for idx in range(mid_idx, len(right_pts)):
        if dev_R[idx] > 6.0:
            br_idx = idx - 1
            break
    br_idx = max(br_idx, mid_idx)
    P_BR = right_pts[br_idx].copy()

    # 6. Smooth Boundary Curves
    N_pts = 30
    xs_top = np.linspace(P_TL[0], P_TR[0], N_pts)
    ys_top = []
    for x in xs_top:
        x_int = int(np.clip(x, 0, w - 1))
        ys = np.where(mask[:, x_int] > 127)[0]
        ys_top.append(float(np.min(ys)) if len(ys) > 0 else P_TL[1])
    poly_top = np.polyfit(xs_top, ys_top, deg=2)
    T_x = xs_top
    T_y = np.polyval(poly_top, T_x)
    T_y[0], T_y[-1] = P_TL[1], P_TR[1]

    xs_bot = np.linspace(P_BL[0], P_BR[0], N_pts)
    ys_bot = []
    for x in xs_bot:
        x_int = int(np.clip(x, 0, w - 1))
        ys = np.where(mask[:, x_int] > 127)[0]
        ys_bot.append(float(np.max(ys)) if len(ys) > 0 else P_BL[1])
    poly_bot = np.polyfit(xs_bot, ys_bot, deg=2)
    B_x = xs_bot
    B_y = np.polyval(poly_bot, B_x)
    B_y[0], B_y[-1] = P_BL[1], P_BR[1]

    return P_TL, P_TR, P_BL, P_BR, np.column_stack((T_x, T_y)), np.column_stack((B_x, B_y))

# Test on Castillo de Liria
mask_liria = cv2.imread("scratch_debug/liria_mask.png", cv2.IMREAD_GRAYSCALE)
crop_liria = cv2.imread("scratch_debug/liria_crop.png")
P_TL, P_TR, P_BL, P_BR, T_curve, B_curve = extract_exact_mask_corners(mask_liria)

vis = crop_liria.copy()
# Draw semitransparent green mask
mask_bool = mask_liria > 127
green_layer = np.zeros_like(vis)
green_layer[mask_bool] = [40, 225, 60]
vis[mask_bool] = cv2.addWeighted(crop_liria[mask_bool], 0.65, green_layer[mask_bool], 0.35, 0)

# Draw CV Vector lines
cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

out_file = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\liria_true_vector_corners.png"
cv2.imwrite(out_file, vis)

print("P_TL:", P_TL)
print("P_TR:", P_TR)
print("P_BL:", P_BL)
print("P_BR:", P_BR)
print(f"Saved {out_file} successfully!")
