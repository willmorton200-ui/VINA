import cv2
import numpy as np
import os
import matplotlib.pyplot as plt

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

# Let's inspect the mask contour points
# Find the actual mask bottom edge
y_indices, x_indices = np.where(crop_mask > 127)

# For every x in range(w), find min_y (top edge) and max_y (bottom edge)
xs = np.arange(w)
top_profile = []
bot_profile = []
for x in xs:
    col_ys = np.where(crop_mask[:, x] > 127)[0]
    if len(col_ys) > 0:
        top_profile.append((x, float(np.min(col_ys))))
        bot_profile.append((x, float(np.max(col_ys))))

top_profile = np.array(top_profile) # (x, y)
bot_profile = np.array(bot_profile) # (x, y)

print(f"Mask bounding box: x in [{top_profile[0,0]}, {top_profile[-1,0]}], y in [{np.min(top_profile[:,1])}, {np.max(bot_profile[:,1])}]")
print(f"Bottom profile extremes: x_min={bot_profile[0,0]}, y_at_xmin={bot_profile[0,1]}; x_max={bot_profile[-1,0]}, y_at_xmax={bot_profile[-1,1]}; max_y={np.max(bot_profile[:,1])} at x={bot_profile[np.argmax(bot_profile[:,1]), 0]}")

# Let's plot the raw mask bottom profile and overlay on the image
vis = crop_bgr.copy()
for pt in bot_profile:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 2, (0, 0, 255), -1)

for pt in top_profile:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 2, (255, 0, 0), -1)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
cv2.imwrite(os.path.join(artifacts_dir, "castillo_raw_profiles_debug.png"), vis)
print("Saved castillo_raw_profiles_debug.png successfully!")
