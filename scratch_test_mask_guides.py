import cv2
import numpy as np

# Load SAM mask and cropped image
mask = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\sam_mask_raw.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\vector_stage1_retinex.png")
if crop is None:
    crop = cv2.imread(r"D:\VINA\outputs\test_vector_sam_alma\photo_2026-08-11_21-10-16\stage1_retinex.png")

h, w = mask.shape[:2]

# 1. Extract exact left and right edge profile from the SAM mask
y_indices, x_indices = np.where(mask > 127)
y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))

left_pts = []
right_pts = []

# Scan every row in the middle 80% of height to avoid corner roundings
for y in range(y_min + int((y_max - y_min) * 0.05), y_max - int((y_max - y_min) * 0.05), 3):
    row_xs = np.where(mask[y, :] > 127)[0]
    if len(row_xs) > 10:
        left_pts.append([float(row_xs[0]), float(y)])
        right_pts.append([float(row_xs[-1]), float(y)])

left_pts = np.array(left_pts, dtype=np.float32)
right_pts = np.array(right_pts, dtype=np.float32)

# Robust Linear fit for Left and Right Green lines: x = m*y + c
left_poly = np.polyfit(left_pts[:, 1], left_pts[:, 0], deg=1)
right_poly = np.polyfit(right_pts[:, 1], right_pts[:, 0], deg=1)

print(f"True Left Green Line: x = {left_poly[0]:.4f} * y + {left_poly[1]:.2f}")
print(f"True Right Green Line: x = {right_poly[0]:.4f} * y + {right_poly[1]:.2f}")

# 2. Extract Top Red Arc directly from SAM mask top edge
# Top edge: for each column x, find the first white pixel
x_min_top = int(np.polyval(left_poly, y_min + 10))
x_max_top = int(np.polyval(right_poly, y_min + 10))

top_edge_pts = []
for x in range(x_min_top, x_max_top, 2):
    col_ys = np.where(mask[:, x] > 127)[0]
    if len(col_ys) > 0:
        top_edge_pts.append([float(x), float(col_ys[0])])

top_edge_pts = np.array(top_edge_pts, dtype=np.float32)
top_poly = np.polyfit(top_edge_pts[:, 0], top_edge_pts[:, 1], deg=2)
print(f"True Top Red Arc: y = {top_poly[0]:.7f} * x^2 + {top_poly[1]:.4f} * x + {top_poly[2]:.2f}")

# 3. Bottom Arc from Lowest Text Points (РОССИЯ / КРЫМ)
# Binarize to find text connected components
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
binary_mask = cv2.bitwise_and(binary, mask)

num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_mask)
lowest_text_pts = []

for i in range(1, num_labels):
    bx, by, bw, bh, area = stats[i]
    # Filter text in lower 30% of label height
    if by > y_min + (y_max - y_min) * 0.70 and 5 < bh < 80 and 5 < bw < 80 and area > 20:
        # Bottom-most point of character
        lowest_text_pts.append([bx + bw / 2.0, by + bh])

lowest_text_pts = np.array(lowest_text_pts, dtype=np.float32)

if len(lowest_text_pts) >= 4:
    # Fit parabola to lowest text row
    text_bot_poly = np.polyfit(lowest_text_pts[:, 0], lowest_text_pts[:, 1], deg=2)
    # Extrapolate to bottom edge of label
    offset = float(y_max) - float(np.max(lowest_text_pts[:, 1]))
    bot_poly = np.array([text_bot_poly[0], text_bot_poly[1], text_bot_poly[2] + offset])
else:
    # Use top curvature mirrored/shifted
    bot_poly = np.array([top_poly[0], top_poly[1], float(y_max) - top_poly[0] * (((x_min_top + x_max_top)/2.0)**2)])

print(f"True Bottom Arc (from lowest text points): y = {bot_poly[0]:.7f} * x^2 + {bot_poly[1]:.4f} * x + {bot_poly[2]:.2f}")

# 4. VISUALIZATION ON MASK (Matching User's Drawing)
vis_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

# Draw Green Left & Right lines
eval_ys = np.linspace(y_min, y_max, 100)
left_line_pts = np.column_stack((np.polyval(left_poly, eval_ys), eval_ys)).astype(np.int32)
right_line_pts = np.column_stack((np.polyval(right_poly, eval_ys), eval_ys)).astype(np.int32)

cv2.polylines(vis_mask, [left_line_pts], False, (0, 255, 0), 6, lineType=cv2.LINE_AA) # Green Left
cv2.polylines(vis_mask, [right_line_pts], False, (0, 255, 0), 6, lineType=cv2.LINE_AA) # Green Right

# Draw Red Top Arc
eval_xs_top = np.linspace(int(np.polyval(left_poly, y_min)), int(np.polyval(right_poly, y_min)), 100)
top_arc_pts = np.column_stack((eval_xs_top, np.polyval(top_poly, eval_xs_top))).astype(np.int32)
cv2.polylines(vis_mask, [top_arc_pts], False, (0, 0, 255), 6, lineType=cv2.LINE_AA) # Red Top

# Draw Bottom Arc
eval_xs_bot = np.linspace(int(np.polyval(left_poly, y_max)), int(np.polyval(right_poly, y_max)), 100)
bot_arc_pts = np.column_stack((eval_xs_bot, np.polyval(bot_poly, eval_xs_bot))).astype(np.int32)
cv2.polylines(vis_mask, [bot_arc_pts], False, (0, 0, 255), 6, lineType=cv2.LINE_AA) # Red Bottom

# Draw lowest text points
for pt in lowest_text_pts:
    cv2.circle(vis_mask, (int(pt[0]), int(pt[1])), 4, (0, 255, 255), -1)

cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\mask_guides_explanation.png", vis_mask)

# 5. VISUALIZATION ON COLOR IMAGE
vis_color = crop.copy()
cv2.polylines(vis_color, [left_line_pts], False, (0, 255, 0), 5, lineType=cv2.LINE_AA)
cv2.polylines(vis_color, [right_line_pts], False, (0, 255, 0), 5, lineType=cv2.LINE_AA)
cv2.polylines(vis_color, [top_arc_pts], False, (0, 0, 255), 5, lineType=cv2.LINE_AA)
cv2.polylines(vis_color, [bot_arc_pts], False, (0, 0, 255), 5, lineType=cv2.LINE_AA)
for pt in lowest_text_pts:
    cv2.circle(vis_color, (int(pt[0]), int(pt[1])), 4, (0, 255, 255), -1)

cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\color_guides_explanation.png", vis_color)
print("Saved mask_guides_explanation.png and color_guides_explanation.png successfully!")
