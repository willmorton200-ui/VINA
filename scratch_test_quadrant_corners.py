import cv2
import numpy as np

def test_extreme_quadrant_corners(mask_path, crop_path, name):
    mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
    crop = cv2.imread(crop_path)
    h, w = mask.shape[:2]

    # Clean mask to single largest component
    binary = np.uint8(mask > 127)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels > 2:
        largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        clean_mask = np.zeros((h, w), dtype=np.uint8)
        clean_mask[labels == largest_label] = 255
        mask = clean_mask

    y_indices, x_indices = np.where(mask > 127)
    x_min, x_max = float(np.min(x_indices)), float(np.max(x_indices))
    y_min, y_max = float(np.min(y_indices)), float(np.max(y_indices))

    # Find external contour
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cnt = max(contours, key=cv2.contourArea)[:, 0, :].astype(np.float64) # (N, 2) [x, y]

    # Extreme Quadrant Corner Optimization:
    # Distance to the 4 bounding box corners
    # Normalize coordinates to [0, 1]
    norm_x = (cnt[:, 0] - x_min) / max(x_max - x_min, 1.0)
    norm_y = (cnt[:, 1] - y_min) / max(y_max - y_min, 1.0)

    score_TL = norm_x + norm_y
    score_TR = (1.0 - norm_x) + norm_y
    score_BL = norm_x + (1.0 - norm_y)
    score_BR = (1.0 - norm_x) + (1.0 - norm_y)

    P_TL = cnt[np.argmin(score_TL)]
    P_TR = cnt[np.argmin(score_TR)]
    P_BL = cnt[np.argmin(score_BL)]
    P_BR = cnt[np.argmin(score_BR)]

    # Extract Top and Bottom curve points between corners:
    # For Top curve: take the contour points that lie on the upper boundary (or column-wise min_y) between P_TL[0] and P_TR[0]
    xs_top = np.linspace(P_TL[0], P_TR[0], 35)
    ys_top = []
    for x in xs_top:
        x_int = int(np.clip(round(x), 0, w - 1))
        col_ys = np.where(mask[:, x_int] > 127)[0]
        ys_top.append(float(np.min(col_ys)) if len(col_ys) > 0 else P_TL[1])
    poly_top = np.polyfit(xs_top, ys_top, deg=2)
    T_x = xs_top
    T_y = np.polyval(poly_top, T_x)
    T_y[0], T_y[-1] = P_TL[1], P_TR[1]

    # For Bottom curve: take column-wise max_y between P_BL[0] and P_BR[0]
    xs_bot = np.linspace(P_BL[0], P_BR[0], 35)
    ys_bot = []
    for x in xs_bot:
        x_int = int(np.clip(round(x), 0, w - 1))
        col_ys = np.where(mask[:, x_int] > 127)[0]
        ys_bot.append(float(np.max(col_ys)) if len(col_ys) > 0 else P_BL[1])
    poly_bot = np.polyfit(xs_bot, ys_bot, deg=2)
    B_x = xs_bot
    B_y = np.polyval(poly_bot, B_x)
    B_y[0], B_y[-1] = P_BL[1], P_BR[1]

    # Render Visual Overlay
    vis = crop.copy()
    mask_2d = mask > 127
    green_layer = crop.copy()
    green_layer[mask_2d] = [40, 225, 60]
    vis[mask_2d] = cv2.addWeighted(crop[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

    # Blue lateral lines
    cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4, cv2.LINE_AA)
    cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4, cv2.LINE_AA)

    # Green boundary curves
    cv2.polylines(vis, [np.column_stack((T_x, T_y)).astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)
    cv2.polylines(vis, [np.column_stack((B_x, B_y)).astype(np.int32)], False, (0, 255, 0), 4, lineType=cv2.LINE_AA)

    # 4 Corner Green Dots
    for pt in [P_TL, P_TR, P_BL, P_BR]:
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1, cv2.LINE_AA)

    out_file = rf"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\{name}_quadrant_extreme_vector.png"
    cv2.imwrite(out_file, vis)
    print(f"[{name}] P_TL: {P_TL}, P_TR: {P_TR}, P_BL: {P_BL}, P_BR: {P_BR}")
    print(f"  -> Saved {out_file}")

test_extreme_quadrant_corners("scratch_debug/michel_mask.png", "scratch_debug/michel_crop.png", "michel")
test_extreme_quadrant_corners("scratch_debug/liria_mask.png", "scratch_debug/liria_crop.png", "liria")
