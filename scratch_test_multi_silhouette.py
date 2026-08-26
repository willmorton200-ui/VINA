import cv2
import numpy as np
import os

def vectorize_strict_silhouette(mask: np.ndarray):
    h, w = mask.shape[:2]
    
    # 1. Clean to single largest component
    binary = np.uint8(mask > 127)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels > 2:
        largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        clean_mask = np.zeros_like(mask)
        clean_mask[labels == largest_label] = 255
        mask = clean_mask

    y_indices, x_indices = np.where(mask > 127)
    x_min, x_max = int(np.min(x_indices)), int(np.max(x_indices))
    y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
    H = y_max - y_min

    # 2. Fit Left and Right Silhouette Wall Lines
    left_wall_pts = []
    right_wall_pts = []

    for y in range(int(y_min + 0.12 * H), int(y_min + 0.70 * H), 2):
        row_xs = np.where(mask[y, :] > 127)[0]
        if len(row_xs) > 0:
            left_wall_pts.append((row_xs[0], y))
            right_wall_pts.append((row_xs[-1], y))

    left_wall_pts = np.array(left_wall_pts)
    right_wall_pts = np.array(right_wall_pts)

    poly_left_line = np.polyfit(left_wall_pts[:, 1], left_wall_pts[:, 0], deg=1)
    poly_right_line = np.polyfit(right_wall_pts[:, 1], right_wall_pts[:, 0], deg=1)

    # Shift strictly to outermost silhouette
    poly_left_line[1] = np.percentile(left_wall_pts[:, 0] - poly_left_line[0] * left_wall_pts[:, 1], 5)
    poly_right_line[1] = np.percentile(right_wall_pts[:, 0] - poly_right_line[0] * right_wall_pts[:, 1], 95)

    # 3. Robust Top and Bottom Profile Curves
    xs_sample = np.linspace(x_min + 0.10 * (x_max - x_min), x_max - 0.10 * (x_max - x_min), 60)
    raw_bots = []
    raw_tops = []
    valid_xs = []

    for x in xs_sample:
        x_int = int(round(x))
        ys = np.where(mask[:, x_int] > 127)[0]
        if len(ys) > 0:
            valid_xs.append(x)
            raw_tops.append(float(np.min(ys)))
            raw_bots.append(float(np.max(ys)))

    valid_xs = np.array(valid_xs)
    raw_tops = np.array(raw_tops)
    raw_bots = np.array(raw_bots)

    poly_bot = np.polyfit(valid_xs, raw_bots, deg=2)
    for _ in range(5):
        fitted = np.polyval(poly_bot, valid_xs)
        res = raw_bots - fitted
        inliers = res <= np.median(res) + 2.5
        if np.sum(inliers) >= 10:
            poly_bot = np.polyfit(valid_xs[inliers], raw_bots[inliers], deg=2)

    poly_top = np.polyfit(valid_xs, raw_tops, deg=2)
    for _ in range(5):
        fitted = np.polyval(poly_top, valid_xs)
        res = fitted - raw_tops
        inliers = res <= np.median(res) + 2.5
        if np.sum(inliers) >= 10:
            poly_top = np.polyfit(valid_xs[inliers], raw_tops[inliers], deg=2)

    # 4. Corner Points
    x_BL_est = np.polyval(poly_left_line, y_max - 0.15 * H)
    y_BL = float(np.polyval(poly_bot, x_BL_est))
    x_BL = float(np.polyval(poly_left_line, y_BL))
    P_BL = np.array([x_BL, y_BL])

    x_BR_est = np.polyval(poly_right_line, y_max - 0.15 * H)
    y_BR = float(np.polyval(poly_bot, x_BR_est))
    x_BR = float(np.polyval(poly_right_line, y_BR))
    P_BR = np.array([x_BR, y_BR])

    x_TL_est = np.polyval(poly_left_line, y_min + 0.10 * H)
    y_TL = float(np.polyval(poly_top, x_TL_est))
    x_TL = float(np.polyval(poly_left_line, y_TL))
    P_TL = np.array([x_TL, y_TL])

    x_TR_est = np.polyval(poly_right_line, y_min + 0.10 * H)
    y_TR = float(np.polyval(poly_top, x_TR_est))
    x_TR = float(np.polyval(poly_right_line, y_TR))
    P_TR = np.array([x_TR, y_TR])

    N_pts = 35
    T_x = np.linspace(P_TL[0], P_TR[0], N_pts)
    T_y = np.polyval(poly_top, T_x)
    T_y[0], T_y[-1] = P_TL[1], P_TR[1]

    B_x = np.linspace(P_BL[0], P_BR[0], N_pts)
    B_y = np.polyval(poly_bot, B_x)
    B_y[0], B_y[-1] = P_BL[1], P_BR[1]

    return P_TL, P_TR, P_BL, P_BR, np.column_stack((T_x, T_y)), np.column_stack((B_x, B_y))

# Test on 4 bottles
test_cases = [
    ("Barakiani", "scratch_debug/barakiani_raw_mask.png"),
    ("Michel Schneider", "scratch_debug/michel_mask.png"),
    ("Castillo de Liria", "scratch_debug/liria_mask.png"),
]

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"

for name, mask_file in test_cases:
    if not os.path.exists(mask_file):
        continue
    mask = cv2.imread(mask_file, cv2.IMREAD_GRAYSCALE)
    P_TL, P_TR, P_BL, P_BR, T_curve, B_curve = vectorize_strict_silhouette(mask)
    
    vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
    green_layer = np.zeros_like(vis)
    green_layer[mask > 127] = [40, 225, 60]
    vis = cv2.addWeighted(vis, 0.55, green_layer, 0.45, 0)
    
    cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
    cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)
        
    out_name = f"{name.lower().replace(' ', '_')}_strict_silhouette_vis.png"
    cv2.imwrite(os.path.join(artifacts_dir, out_name), vis)
    print(f"[{name}] Saved {out_name} with P_TL={P_TL}, P_BL={P_BL}")
