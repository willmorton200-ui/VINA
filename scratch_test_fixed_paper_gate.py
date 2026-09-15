import cv2
import numpy as np

def fix_paper_gate(img_bgr, raw_sam_mask):
    """
    Fixed Paper Gate:
    1. Does NOT eat inside the label (preserves dark text, illustrations, and ornaments).
    2. Only cleans outside background and fills internal holes.
    3. Retains largest connected component.
    """
    if raw_sam_mask is None or np.sum(raw_sam_mask > 127) == 0:
        return raw_sam_mask
        
    mask = np.uint8(raw_sam_mask > 127) * 255
    
    # Fill internal holes (so dark letters and ornaments inside are 100% preserved)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        clean_mask = np.zeros_like(mask)
        # Draw filled largest contour
        largest_cnt = max(cnts, key=cv2.contourArea)
        cv2.drawContours(clean_mask, [largest_cnt], -1, 255, -1)
        mask = clean_mask
        
    # Morphological closing with ellipse
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask_closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    
    return mask_closed

# Test on Barakiani
img = cv2.imread('test_dataset/butilki/photo_2026-08-10_12-34-31.jpg')
from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

# Test on both labels
mask_upper, _ = p1.sam_refiner.refine_mask(img, [239, 366, 673, 685])
mask_lower, _ = p1.sam_refiner.refine_mask(img, [241, 670, 654, 1115])

clean_upper = fix_paper_gate(img, mask_upper)
clean_lower = fix_paper_gate(img, mask_lower)

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
cv2.imwrite(f"{artifacts_dir}/barakiani_fixed_upper_mask.png", clean_upper)
cv2.imwrite(f"{artifacts_dir}/barakiani_fixed_lower_mask.png", clean_lower)
print("Saved fixed clean masks without any holes or tears!")
