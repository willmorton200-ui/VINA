import cv2
import numpy as np

mask = cv2.imread("scratch_debug/michel_mask.png", cv2.IMREAD_GRAYSCALE)
crop = cv2.imread("scratch_debug/michel_crop.png")
h, w = mask.shape[:2]

# Let's find the contour of the mask:
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea)[:, 0, :]

# Draw contour on crop:
vis_cnt = crop.copy()
cv2.drawContours(vis_cnt, contours, -1, (0, 0, 255), 2)
cv2.imwrite(r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d\michel_raw_mask_contour.png", vis_cnt)

print(f"Mask bounding rect: {cv2.boundingRect(cnt)}")
print("Saved michel_raw_mask_contour.png!")
