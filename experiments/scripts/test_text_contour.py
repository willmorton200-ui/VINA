import cv2
import numpy as np
import os
from rapidocr_onnxruntime import RapidOCR

def get_lowest_point(contour):
    """Returns the (x, y) of the lowest pixel in the contour (max Y)."""
    # contour is shape (N, 1, 2)
    pts = contour.reshape(-1, 2)
    max_y_idx = np.argmax(pts[:, 1])
    return pts[max_y_idx]

def main():
    img_path = r"D:\VINA\test_dataset\butilki\monastyrskaya_izba.jpg"
    img = cv2.imread(img_path)
    if img is None:
        print("Image not found!")
        return

    out_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ff223942-8c56-4dbf-86d0-d0a36dc4c092\scratch"
    os.makedirs(out_dir, exist_ok=True)

    ocr = RapidOCR(det_unclip_ratio=1.9, det_db_box_thresh=0.38)
    results, _ = ocr(img)
    
    img_w = img.shape[1]
    vis_global = img.copy()
    
    if not results:
        print("No text found!")
        return

    for bbox, text, conf in results:
        pts = np.array(bbox, np.int32)
        x_coords = pts[:, 0]
        y_coords = pts[:, 1]
        
        w = np.max(x_coords) - np.min(x_coords)
        if w < img_w * 0.3: # Only process lines spanning > 30% width
            continue
            
        print(f"Processing: {text}")
        
        margin = 5
        x_min, x_max = max(0, np.min(x_coords) - margin), min(img.shape[1], np.max(x_coords) + margin)
        y_min, y_max = max(0, np.min(y_coords) - margin), min(img.shape[0], np.max(y_coords) + margin)
        
        crop = img[y_min:y_max, x_min:x_max]
        if crop.size == 0:
            continue
            
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_contours = []
        crop_h = y_max - y_min
        crop_area = (y_max - y_min) * (x_max - x_min)
        
        for c in contours:
            cx, cy, cw, ch = cv2.boundingRect(c)
            # Filter criteria adapted for smaller fonts
            if cv2.contourArea(c) > crop_area * 0.002 and ch > crop_h * 0.2:
                valid_contours.append(c)
                
        valid_contours.sort(key=lambda c: cv2.boundingRect(c)[0])
        
        if len(valid_contours) < 3:
            print(f"Not enough letters for {text}")
            continue
            
        idx_first = 0
        idx_mid = len(valid_contours) // 2
        idx_last = len(valid_contours) - 1
        
        selected_contours = [valid_contours[idx_first], valid_contours[idx_mid], valid_contours[idx_last]]
        pts_global = []
        
        for c in selected_contours:
            lowest_pt = get_lowest_point(c)
            gx = lowest_pt[0] + x_min
            gy = lowest_pt[1] + y_min
            pts_global.append([gx, gy])
            
            # Draw blue dots on original image for visualization
            cv2.circle(vis_global, (int(gx), int(gy)), 5, (255, 0, 0), -1)
            cv2.circle(vis_global, (int(gx), int(gy)), 7, (255, 255, 255), 2)
            
        pts_global = np.array(pts_global, dtype=np.float64)
        poly = np.polyfit(pts_global[:, 0], pts_global[:, 1], 2)
        
        # Extend parabola to the edges (later it will be to lateral guides, here to image edges for demo)
        xs = np.linspace(0, img_w, 100)
        ys = np.polyval(poly, xs)
        curve = np.column_stack((xs, ys)).astype(np.int32)
        cv2.polylines(vis_global, [curve], False, (0, 0, 255), 2, cv2.LINE_AA)
        
    cv2.imwrite(os.path.join(out_dir, "05_all_parabolas.png"), vis_global)
    print("Done. Saved 05_all_parabolas.png")

if __name__ == "__main__":
    main()
