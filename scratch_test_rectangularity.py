import cv2
import numpy as np

def compute_rectangularity(component_mask: np.ndarray) -> float:
    """
    Computes rectangularity index: Area(mask) / Area(Minimum Area Bounding Box).
    Values close to 1.0 indicate perfect rectangles.
    Values < 0.6 indicate triangles, diamonds, houses, or non-rectangular shapes.
    """
    contours, _ = cv2.findContours(component_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    if area < 100:
        return 0.0
    rect = cv2.minAreaRect(cnt)
    rect_w, rect_h = rect[1]
    rect_area = rect_w * rect_h
    if rect_area <= 0:
        return 0.0
    return float(area / rect_area)

# Test on the two masks of Terra Argenta
mask_upper = cv2.imread("scratch_debug/terra_mask_upper.png", cv2.IMREAD_GRAYSCALE)
mask_lower = cv2.imread("scratch_debug/terra_mask_lower.png", cv2.IMREAD_GRAYSCALE)

rect_upper = compute_rectangularity(mask_upper)
rect_lower = compute_rectangularity(mask_lower)

print(f"Upper Label (Emblem) Rectangularity: {rect_upper:.4f}")
print(f"Lower Label (Rectangle) Rectangularity: {rect_lower:.4f}")
