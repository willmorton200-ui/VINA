import cv2
import numpy as np

mask = cv2.imread(r"d:\VINA\debug_masks\03_largest_comp.png", 0)
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

x_min = 0
x_max = mask.shape[1] - 1

top_ys = []
for x in range(int(x_min), int(x_max) + 1):
    if x >= 0 and x < mask_closed.shape[1]:
        ys = np.where(mask_closed[:, x] > 127)[0]
        if len(ys) > 0:
            top_ys.append(ys[0])
            
print(f"len(top_ys): {len(top_ys)}")
top_ys = np.array(top_ys)
n = len(top_ys)
print(top_ys)
mid = top_ys[n//3:2*n//3]
edges = np.concatenate([top_ys[:n//6], top_ys[-n//6:]])
print(f"Mid len: {len(mid)}, Edges len: {len(edges)}")
print(f"Mid median: {np.median(mid)}, Edges median: {np.median(edges)}")
sag = float(np.median(mid) - np.median(edges))
print(f"Macro sag: {sag}")
