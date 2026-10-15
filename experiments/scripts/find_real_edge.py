import cv2
import numpy as np

img_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ff223942-8c56-4dbf-86d0-d0a36dc4c092\.user_uploaded\media_1789616885445.png"
img = cv2.imread(img_path)
if img is None:
    print("Failed to load image")
    exit()

# The user uploaded an image with UI drawings on it (red dots, blue/green lines).
# We want to find the REAL top edge of the white label.
# The white label is very bright. We can use color thresholding or just grayscale thresholding.
# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# The white paper is very bright, the yellow liquid is darker.
# Let's apply a threshold.
_, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

# Find the topmost row of the white paper for each column
h, w = thresh.shape
out_img = img.copy()

# We only care about the middle area to avoid the blue lines drawn by UI
start_x = int(w * 0.15)
end_x = int(w * 0.85)

top_edge_pts = []
for x in range(start_x, end_x):
    # Find first white pixel from top
    col = thresh[:, x]
    white_pixels = np.where(col == 255)[0]
    if len(white_pixels) > 0:
        y = white_pixels[0]
        # Check if it's the real label (y should be somewhat in the middle, not at the very top)
        if y > h * 0.1:
            top_edge_pts.append((x, y))

if len(top_edge_pts) > 0:
    top_edge_pts = np.array(top_edge_pts)
    # Fit a quadratic curve to the top edge
    poly = np.polyfit(top_edge_pts[:, 0], top_edge_pts[:, 1], deg=2)
    
    # Draw the true curve in thick magenta
    for x in range(start_x, end_x):
        y = int(np.polyval(poly, x))
        cv2.circle(out_img, (x, y), 2, (255, 0, 255), -1)
        
    cv2.putText(out_img, "REAL LABEL TOP EDGE", (start_x, int(np.polyval(poly, start_x)) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)

out_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ff223942-8c56-4dbf-86d0-d0a36dc4c092\real_top_edge.png"
cv2.imwrite(out_path, out_img)
print(f"Saved to {out_path}")
