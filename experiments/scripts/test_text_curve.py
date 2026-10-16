import cv2
import numpy as np
import sys
import os

# Add pipeline to path
sys.path.append(r"d:\VINA\pipeline")
from stage5_ocr import Stage5OCRDecoder

ocr = Stage5OCRDecoder()
img = cv2.imread(r"d:\VINA\test_dataset\cam\757_chteau-le-grand-vostock-le-chene-royal-reserve.jpeg")
img_crop = img[0:388, 3:297]

res = ocr.process(img_crop)

debug = img_crop.copy()
pts = []
for block in res["text_blocks"]:
    poly = block["polygon"] # [[x,y], [x,y], [x,y], [x,y]] (TL, TR, BR, BL)
    # Take bottom center
    if len(poly) == 4:
        br = poly[2]
        bl = poly[3]
        cx = (bl[0] + br[0]) / 2.0
        cy = (bl[1] + br[1]) / 2.0
        pts.append([cx, cy])
        
        cv2.circle(debug, (int(cx), int(cy)), 2, (0, 0, 255), -1)
        # Draw poly
        pts_poly = np.array(poly, np.int32)
        cv2.polylines(debug, [pts_poly], True, (0, 255, 0), 1)

cv2.imwrite(r"d:\VINA\debug_masks\ocr_blocks.png", debug)

pts = np.array(pts)
if len(pts) >= 3:
    # Sort by X to form a single curve trend (or just fit a global parabola)
    # Actually, we have many lines. We can just fit a global 2D polynomial surface 
    # y = A*x^2 + B*x + C*y0 + D  (where y0 is vertical position)
    # Or simpler: for each point, compute its deviation from the linear fit of all points.
    pass

print(f"Found {len(pts)} text blocks.")

