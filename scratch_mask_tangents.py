import cv2
import numpy as np

mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

# Find largest contour
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea).squeeze() # (N, 2)

# Find convex hull
hull = cv2.convexHull(cnt).squeeze() # (M, 2)

# Find the leftmost points (x < cx) and rightmost points (x >= cx)
cx = np.mean(cnt[:, 0])
cy = np.mean(cnt[:, 1])

# On the left side: find the tangent line to the hull
# The tangent line x = m*y + c passes through hull points and has x >= m*y + c for all points
# We fit a line to the left side of the hull between y in [0.15*H, 0.85*H]
y_min = int(np.min(cnt[:, 1]))
y_max = int(np.max(cnt[:, 1]))
h_span = y_max - y_min

left_pts = cnt[(cnt[:, 0] < cx) & (cnt[:, 1] > y_min + 0.1 * h_span) & (cnt[:, 1] < y_max - 0.1 * h_span)]
right_pts = cnt[(cnt[:, 0] >= cx) & (cnt[:, 1] > y_min + 0.1 * h_span) & (cnt[:, 1] < y_max - 0.1 * h_span)]

# Extract leftmost point for each unique y
unique_ys_l = np.unique(left_pts[:, 1])
leftmost_pts = []
for y in unique_ys_l:
    xs = left_pts[left_pts[:, 1] == y, 0]
    leftmost_pts.append([float(np.min(xs)), float(y)])
leftmost_pts = np.array(leftmost_pts)

unique_ys_r = np.unique(right_pts[:, 1])
rightmost_pts = []
for y in unique_ys_r:
    xs = right_pts[right_pts[:, 1] == y, 0]
    rightmost_pts.append([float(np.max(xs)), float(y)])
rightmost_pts = np.array(rightmost_pts)

# Fit linear Blue Left and Blue Right tangents: x = m*y + c
m_l, c_l = np.polyfit(leftmost_pts[:, 1], leftmost_pts[:, 0], deg=1)
m_r, c_r = np.polyfit(rightmost_pts[:, 1], rightmost_pts[:, 0], deg=1)

print(f"Left Tangent Line:  x = {m_l:.5f} * y + {c_l:.2f}")
print(f"Right Tangent Line: x = {m_r:.5f} * y + {c_r:.2f}")

# Top profile points: for each x between left tangent at top and right tangent at top
x_tl = m_l * (y_min + 15) + c_l
x_tr = m_r * (y_min + 15) + c_r

top_pts = []
for x in range(int(x_tl), int(x_tr)):
    ys = cnt[cnt[:, 0] == x, 1]
    if len(ys) > 0:
        top_pts.append([float(x), float(np.min(ys))])
top_pts = np.array(top_pts)

top_poly = np.polyfit(top_pts[:, 0], top_pts[:, 1], deg=2)
print("Top Arc Poly:", top_poly)

# Bottom profile points: lowest text/mask profile
x_bl = m_l * (y_max - 15) + c_l
x_br = m_r * (y_max - 15) + c_r

# Quadratic bottom curve: centered at cx
curv_top = top_poly[0]
cx_bot = (x_bl + x_br) / 2.0
bot_poly = np.array([-curv_top * 0.9, 2.0 * curv_top * 0.9 * cx_bot, y_max - (curv_top * 0.9) * (cx_bot ** 2)])

# 4 Corner Vertices
p_tl = (int(x_tl), int(np.polyval(top_poly, x_tl)))
p_tr = (int(x_tr), int(np.polyval(top_poly, x_tr)))
p_br = (int(x_br), int(np.polyval(bot_poly, x_br)))
p_bl = (int(x_bl), int(np.polyval(bot_poly, x_bl)))

print("P_TL:", p_tl, "P_TR:", p_tr, "P_BR:", p_br, "P_BL:", p_bl)

# Generate high-resolution vectors
N = 120
xs_top = np.linspace(p_tl[0], p_tr[0], N)
ys_top = np.polyval(top_poly, xs_top)
vec_top = np.column_stack((xs_top, ys_top)).astype(np.int32)

ys_r = np.linspace(p_tr[1], p_br[1], N)
xs_r = m_r * ys_r + c_r
vec_r = np.column_stack((xs_r, ys_r)).astype(np.int32)

xs_bot = np.linspace(p_br[0], p_bl[0], N)
ys_bot = np.polyval(bot_poly, xs_bot)
vec_bot = np.column_stack((xs_bot, ys_bot)).astype(np.int32)

ys_l = np.linspace(p_bl[1], p_tl[1], N)
xs_l = m_l * ys_l + c_l
vec_l = np.column_stack((xs_l, ys_l)).astype(np.int32)

# Full closed vector polygon
vector_shape = np.vstack([vec_top, vec_r, vec_bot, vec_l])

# -------------------------------------------------------------
# RENDER ON THE BINARY MASK
# -------------------------------------------------------------
vis = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

# Semi-transparent filled region
overlay = vis.copy()
cv2.fillPoly(overlay, [vector_shape], (255, 235, 180)) # light cyan fill
cv2.addWeighted(overlay, 0.35, vis, 0.65, 0, vis)

# Draw BLUE SIDE TANGENT LINES (extending past top/bottom)
eval_ys_ext = np.linspace(y_min - 40, y_max + 40, 100)
left_line_ext = np.column_stack((m_l * eval_ys_ext + c_l, eval_ys_ext)).astype(np.int32)
right_line_ext = np.column_stack((m_r * eval_ys_ext + c_r, eval_ys_ext)).astype(np.int32)

cv2.polylines(vis, [left_line_ext], False, (255, 140, 0), 6, lineType=cv2.LINE_AA)  # Blue Left Tangent (BGR)
cv2.polylines(vis, [right_line_ext], False, (255, 140, 0), 6, lineType=cv2.LINE_AA) # Blue Right Tangent (BGR)

# Draw RED TOP ARC VECTOR
cv2.polylines(vis, [vec_top], False, (0, 0, 255), 6, lineType=cv2.LINE_AA) # Red Top Arc

# Draw RED BOTTOM ARC VECTOR
cv2.polylines(vis, [vec_bot], False, (0, 0, 255), 6, lineType=cv2.LINE_AA) # Red Bottom Arc

# Draw Vector Outline Border (Yellow)
cv2.polylines(vis, [vector_shape], True, (0, 255, 255), 2, lineType=cv2.LINE_AA)

# Draw Corner vertices with white/cyan markers
for pt, label in [(p_tl, "TL (x1,y1)"), (p_tr, "TR (x2,y2)"), (p_br, "BR (x3,y3)"), (p_bl, "BL (x4,y4)")]:
    cv2.circle(vis, pt, 9, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, pt, 6, (0, 0, 255), -1, cv2.LINE_AA)
    # Text offset
    tx = pt[0] + 15 if pt[0] < cx else pt[0] - 170
    ty = pt[1] - 10 if pt[1] < cy else pt[1] + 25
    cv2.putText(vis, label, (int(tx), int(ty)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA)

out_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\mask_vector_tangents.png"
cv2.imwrite(out_path, vis)
print("Saved perfect mask_vector_tangents.png!")
