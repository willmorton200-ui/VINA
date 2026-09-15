import cv2
import numpy as np
import os
import matplotlib.pyplot as plt

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"

img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-29.jpg')
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()

mask_red, _ = p1.sam_refiner.refine_mask(img, [0, 273, 463, 832])
mask_white, _ = p1.sam_refiner.refine_mask(img, [479, 263, 960, 840])

def analyze_bottle_corners(crop_bgr, mask_crop, name):
    h, w = crop_bgr.shape[:2]
    
    # 1. Clean mask
    binary = np.uint8(mask_crop > 127)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels > 2:
        largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        clean_mask = np.zeros_like(mask_crop)
        clean_mask[labels == largest_label] = 255
        mask_crop = clean_mask

    # Morphological closing
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask_closed = cv2.morphologyEx(mask_crop, cv2.MORPH_CLOSE, kernel)
    
    # 2. Find External Contour
    contours, _ = cv2.findContours(mask_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        print("No contours found!")
        return
    cnt = max(contours, key=cv2.contourArea) # shape (N, 1, 2)
    pts = cnt.squeeze(1) # shape (N, 2)
    
    # Let's inspect bounding box
    x, y, bw, bh = cv2.boundingRect(cnt)
    print(f"\n--- {name} ---")
    print(f"Bounding rect: x={x}, y={y}, w={bw}, h={bh}")
    
    # METHOD 1: Contour Extreme Quadrant Points / Convex Hull Extreme Points
    # P_TL: minimizes (x + y) or (x + 1.5*y) or top-left corner projection
    # P_TR: minimizes (-x + y) or (-x + 1.5*y)
    # P_BL: minimizes (x - y) or (x - 1.5*y)
    # P_BR: minimizes (-x - y) or (-x - 1.5*y)
    
    # Let's compute normalized coordinates
    xs = pts[:, 0].astype(np.float32)
    ys = pts[:, 1].astype(np.float32)
    
    # METHOD 2: Lateral Line Fitting + Intersection with Top/Bottom Contour Profiles
    # Extract left-most x for each y and right-most x for each y
    unique_ys = np.unique(ys.astype(int))
    left_edge = []
    right_edge = []
    for cur_y in unique_ys:
        xs_at_y = xs[ys.astype(int) == cur_y]
        if len(xs_at_y) > 0:
            left_edge.append([np.min(xs_at_y), cur_y])
            right_edge.append([np.max(xs_at_y), cur_y])
    left_edge = np.array(left_edge)
    right_edge = np.array(right_edge)
    
    # Lateral lines from middle 50%
    y_min, y_max = np.min(ys), np.max(ys)
    H = y_max - y_min
    L_mid = left_edge[(left_edge[:, 1] >= y_min + 0.20 * H) & (left_edge[:, 1] <= y_min + 0.80 * H)]
    R_mid = right_edge[(right_edge[:, 1] >= y_min + 0.20 * H) & (right_edge[:, 1] <= y_min + 0.80 * H)]
    
    poly_L = np.polyfit(L_mid[:, 1], L_mid[:, 0], deg=1)
    poly_R = np.polyfit(R_mid[:, 1], R_mid[:, 0], deg=1)
    
    # Top endpoints: highest y on left_edge and right_edge, or intersection with top curve
    # Let's find the exact top-left and top-right points on the mask contour
    # Top-left is the start of left_edge:
    pt_tl_edge = left_edge[np.argmin(left_edge[:, 1])] # minimum y on left edge
    pt_tr_edge = right_edge[np.argmin(right_edge[:, 1])] # minimum y on right edge
    
    # Bottom endpoints: maximum y on left_edge and right_edge
    pt_bl_edge = left_edge[np.argmax(left_edge[:, 1])] # maximum y on left edge
    pt_br_edge = right_edge[np.argmax(right_edge[:, 1])] # maximum y on right edge
    
    print(f"Edge extremes: TL={pt_tl_edge}, TR={pt_tr_edge}, BL={pt_bl_edge}, BR={pt_br_edge}")
    
    # METHOD 3: Contour Curvature / Angle Discontinuity (Corner Detection on Contour)
    # Smooth contour with rolling window and compute curvature k = |x'y'' - y'x''| / (x'^2 + y'^2)^(3/2)
    # or directional derivative: dot product of incoming and outgoing vectors
    k_step = max(5, int(len(pts) * 0.02))
    angles = []
    N = len(pts)
    for i in range(N):
        p_prev = pts[(i - k_step) % N]
        p_curr = pts[i]
        p_next = pts[(i + k_step) % N]
        v1 = p_prev - p_curr
        v2 = p_next - p_curr
        n1 = np.linalg.norm(v1)
        n2 = np.linalg.norm(v2)
        if n1 > 1e-3 and n2 > 1e-3:
            cos_a = np.dot(v1, v2) / (n1 * n2)
            cos_a = np.clip(cos_a, -1.0, 1.0)
            angles.append(cos_a)
        else:
            angles.append(-1.0)
    angles = np.array(angles)
    
    # RDP (Douglas-Peucker) Polygon Approximation
    epsilon = 0.015 * cv2.arcLength(cnt, True)
    approx = cv2.approxPolyDP(cnt, epsilon, True).squeeze(1)
    print(f"RDP approx vertices ({len(approx)} pts):\n{approx}")
    
    # Visual comparison
    vis = crop_bgr.copy()
    # Draw contour
    cv2.drawContours(vis, [cnt], -1, (0, 255, 0), 2)
    
    # Draw lateral lines
    y_span = np.linspace(y_min - 10, y_max + 10, 50)
    x_L = poly_L[0] * y_span + poly_L[1]
    x_R = poly_R[0] * y_span + poly_R[1]
    pts_L = np.column_stack((x_L, y_span)).astype(np.int32)
    pts_R = np.column_stack((x_R, y_span)).astype(np.int32)
    cv2.polylines(vis, [pts_L], False, (255, 140, 0), 2)
    cv2.polylines(vis, [pts_R], False, (255, 140, 0), 2)
    
    # Draw edge extremes (Yellow circles)
    for pt, lbl in zip([pt_tl_edge, pt_tr_edge, pt_bl_edge, pt_br_edge], ["TL_edge", "TR_edge", "BL_edge", "BR_edge"]):
        cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 255), -1)
        cv2.putText(vis, lbl, (int(pt[0])+8, int(pt[1])-8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    # Draw RDP polygon vertices (Magenta)
    for p in approx:
        cv2.circle(vis, (int(p[0]), int(p[1])), 5, (255, 0, 255), -1)
        
    out_path = os.path.join(artifacts_dir, f"corner_analysis_{name}.png")
    cv2.imwrite(out_path, vis)
    print(f"Saved: {out_path}")

analyze_bottle_corners(img[240:860, 460:960], mask_white[240:860, 460:960], "white")
analyze_bottle_corners(img[250:850, 0:470], mask_red[250:850, 0:470], "red")
