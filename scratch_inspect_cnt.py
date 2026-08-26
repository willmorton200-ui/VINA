import cv2
import numpy as np

mask = cv2.imread("scratch_debug/barakiani_raw_mask.png", cv2.IMREAD_GRAYSCALE)
h, w = mask.shape[:2]

# Extract full external contour
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea)[:, 0, :] # (N, 2) [x, y] in clockwise order

print(f"Total contour points: {len(cnt)}")

# Let's inspect the leftmost contour points
left_pts = cnt[cnt[:, 0] <= np.min(cnt[:, 0]) + 30]
print(f"Leftmost X: {np.min(cnt[:, 0])}")
print("Sample leftmost contour points:")
for pt in left_pts[::len(left_pts)//10]:
    print(f"  ({pt[0]}, {pt[1]})")
