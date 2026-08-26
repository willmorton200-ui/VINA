import os
import cv2
import numpy as np
import matplotlib.pyplot as plt

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

# Let's inspect the right flank:
plt.figure(figsize=(12, 10))
y_slices = [100, 200, 300, 400, 450, 500, 530]
for idx, y_val in enumerate(y_slices):
    plt.subplot(len(y_slices), 1, idx + 1)
    xs = np.arange(350, w)
    b = crop_bgr[y_val, 350:w, 0]
    g = crop_bgr[y_val, 350:w, 1]
    r = crop_bgr[y_val, 350:w, 2]
    mask_vals = crop_mask[y_val, 350:w]
    
    plt.plot(xs, r, 'r-', label='R' if idx==0 else "")
    plt.plot(xs, g, 'g-', label='G' if idx==0 else "")
    plt.plot(xs, b, 'b-', label='B' if idx==0 else "")
    plt.plot(xs, mask_vals, 'k--', label='Mask' if idx==0 else "")
    plt.title(f"y = {y_val}")
    plt.grid(True, alpha=0.3)

plt.tight_layout()
artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"
plt.savefig(os.path.join(artifacts_dir, "castillo_right_edge_profiles.png"), dpi=150)
plt.close()

# Also let's inspect the visual crop on the right side
vis_grid = crop_bgr.copy()
for x in range(350, w, 20):
    cv2.line(vis_grid, (x, 0), (x, h), (0, 255, 255), 1)
    cv2.putText(vis_grid, str(x), (x - 10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

cv2.imwrite(os.path.join(artifacts_dir, "castillo_right_edge_grid.png"), vis_grid)
print("Saved right edge profiles and grid successfully!")
