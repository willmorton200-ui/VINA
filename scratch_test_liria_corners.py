import cv2
import numpy as np

mask = cv2.imread("scratch_debug/liria_mask.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread("scratch_debug/liria_crop.png")
h, w = mask.shape[:2]

# 1. Find Contour
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea)[:, 0, :] # (N, 2) [x, y]

# We need the 4 true corners: Top-Left, Top-Right, Bottom-Left, Bottom-Right.
# Method: Douglas-Peucker / Convexity / Corner angle on the contour, or corner response.
# Let's inspect the contour points:
# The label has 4 distinct segments:
# - Left segment: x ~ x_min
# - Right segment: x ~ x_max
# - Top segment: y ~ y_min
# - Bottom segment: y ~ y_max

# Corner TL: min(x + y) or intersection of left edge and top edge
# Corner TR: min(-x + y) or intersection of right edge and top edge
# Corner BL: min(x - y) or intersection of left edge and bottom edge
# Corner BR: min(-x - y) or intersection of right edge and bottom edge

# Let's compute distance to bbox corners / Harris / exact corner vertices:
bbox_x, bbox_y, bbox_w, bbox_h = cv2.boundingRect(cnt)

# For any point (x, y) on contour:
# TL is point minimizing (x - bbox_x) + (y - bbox_y)
# TR is point minimizing (bbox_x + bbox_w - x) + (y - bbox_y)
# BL is point minimizing (x - bbox_x) + (bbox_y + bbox_h - y)
# BR is point minimizing (bbox_x + bbox_w - x) + (bbox_y + bbox_h - y)

# But with curved top/bottom arches, let's check exact curvature / corners:
# Let's calculate the corner points with weighted projection:
# Left boundary points: points where x is close to left_x
# Let's find the true corner where left edge ends and bottom curve starts:

# Let's plot left_x vs y:
y_indices, x_indices = np.where(mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))

left_pts = []
right_pts = []
for y in range(y_min, y_max + 1):
    xs = np.where(mask[y, :] > 127)[0]
    if len(xs) > 0:
        left_pts.append((xs[0], y))
        right_pts.append((xs[-1], y))

left_pts = np.array(left_pts) # (K, 2) [x, y]
right_pts = np.array(right_pts)

# Along left_pts:
# x is small in the middle rows (y ~ 100..500)
# Near top (y ~ 40..60), x increases rapidly towards apex (259, 40)
# Near bottom (y ~ 510..590), x increases rapidly towards apex (229, 590)
# The CORNERS are where dx/dy changes slope (the 'knee' / elbow of the curve)!

dx_top = np.abs(np.diff(left_pts[:len(left_pts)//2, 0]))
dx_bot = np.abs(np.diff(left_pts[len(left_pts)//2:, 0]))

# Knee points:
# Left edge is straight vertical line.
# Let's find the row where left_x is within 5 pixels of min(left_pts[:, 0]):
min_left_x = np.min(left_pts[:, 0])
valid_left_y = left_pts[left_pts[:, 0] <= min_left_x + 12]

P_TL = left_pts[np.argmin(left_pts[:, 0] + 0.5 * left_pts[:, 1])]
# For TL: min(x) in the upper half
upper_left = left_pts[left_pts[:, 1] < (y_min + y_max) // 2]
tl_idx = np.argmin(upper_left[:, 0] + 0.2 * upper_left[:, 1])
P_TL = upper_left[tl_idx].astype(np.float64)

# For BL: min(x) in the lower half
lower_left = left_pts[left_pts[:, 1] >= (y_min + y_max) // 2]
bl_idx = np.argmin(lower_left[:, 0] - 0.2 * lower_left[:, 1])
P_BL = lower_left[bl_idx].astype(np.float64)

# For TR: max(x) in upper half
upper_right = right_pts[right_pts[:, 1] < (y_min + y_max) // 2]
tr_idx = np.argmax(upper_right[:, 0] - 0.2 * upper_right[:, 1])
P_TR = upper_right[tr_idx].astype(np.float64)

# For BR: max(x) in lower half
lower_right = right_pts[right_pts[:, 1] >= (y_min + y_max) // 2]
br_idx = np.argmax(lower_right[:, 0] + 0.2 * lower_right[:, 1])
P_BR = lower_right[br_idx].astype(np.float64)

print(f"P_TL: {P_TL}")
print(f"P_TR: {P_TR}")
print(f"P_BL: {P_BL}")
print(f"P_BR: {P_BR}")

# Let's visualize on mask and on crop:
vis = crop.copy()
cv2.line(vis, (int(P_TL[0]), int(P_TL[1])), (int(P_BL[0]), int(P_BL[1])), (255, 140, 0), 4)
cv2.line(vis, (int(P_TR[0]), int(P_TR[1])), (int(P_BR[0]), int(P_BR[1])), (255, 140, 0), 4)

# Top and Bottom curves:
xs_top = np.linspace(P_TL[0], P_TR[0], 30)
ys_top = []
for x in xs_top:
    x_int = int(np.clip(x, 0, w - 1))
    ys = np.where(mask[:, x_int] > 127)[0]
    ys_top.append(float(np.min(ys)) if len(ys) > 0 else P_TL[1])
poly_top = np.polyfit(xs_top, ys_top, 2)
T_x = xs_top
T_y = np.polyval(poly_top, T_x)
T_y[0], T_y[-1] = P_TL[1], P_TR[1]

xs_bot = np.linspace(P_BL[0], P_BR[0], 30)
ys_bot = []
for x in xs_bot:
    x_int = int(np.clip(x, 0, w - 1))
    ys = np.where(mask[:, x_int] > 127)[0]
    ys_bot.append(float(np.max(ys)) if len(ys) > 0 else P_BL[1])
poly_bot = np.polyfit(xs_bot, ys_bot, 2)
B_x = xs_bot
B_y = np.polyval(poly_bot, B_x)
B_y[0], B_y[-1] = P_BL[1], P_BR[1]

cv2.polylines(vis, [np.column_stack((T_x, T_y)).astype(np.int32)], False, (0, 255, 0), 4)
cv2.polylines(vis, [np.column_stack((B_x, B_y)).astype(np.int32)], False, (0, 255, 0), 4)

for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (255, 255, 255), -1)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 255, 0), -1)

cv2.imwrite("scratch_debug/liria_corrected_vector.png", vis)
print("Saved scratch_debug/liria_corrected_vector.png successfully!")
