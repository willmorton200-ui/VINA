import cv2
import numpy as np

img_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ff223942-8c56-4dbf-86d0-d0a36dc4c092\.user_uploaded\media_1789616885445.png"
img = cv2.imread(img_path)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# Sobel Y (horizontal edges)
sobel_y = cv2.Sobel(blurred, cv2.CV_64F, 0, 1, ksize=3)
abs_sobel_y = np.absolute(sobel_y)
abs_sobel_y = np.uint8(255 * abs_sobel_y / np.max(abs_sobel_y))

# Let's project it horizontally
h, w = abs_sobel_y.shape
projection = np.sum(abs_sobel_y, axis=1)

# We want to find the top edge. It should be in the top half of the image.
# We also want to smooth the projection to avoid local spikes
proj_smoothed = np.convolve(projection, np.ones(5)/5, mode='same')

# Find peaks
import scipy.signal
peaks, properties = scipy.signal.find_peaks(proj_smoothed, prominence=1000)

out_img = img.copy()

print(f"Peaks found at Y: {peaks}")

# Draw the top-most significant peak
if len(peaks) > 0:
    # Filter peaks that are in the top half
    top_peaks = [p for p in peaks if p < h * 0.5]
    if len(top_peaks) > 0:
        # Take the most prominent one? Or the highest one?
        # Let's just draw all of them in blue, and the strongest one in red
        best_peak = -1
        max_prom = 0
        for i, p in enumerate(peaks):
            if p in top_peaks:
                prom = properties['prominences'][i]
                cv2.line(out_img, (0, p), (w, p), (255, 0, 0), 1)
                if prom > max_prom:
                    max_prom = prom
                    best_peak = p
                    
        if best_peak != -1:
            cv2.line(out_img, (0, best_peak), (w, best_peak), (0, 0, 255), 2)
            print(f"Best top peak: {best_peak}")

out_path = r"C:\Users\User\.gemini\antigravity-ide\brain\ff223942-8c56-4dbf-86d0-d0a36dc4c092\edge_peaks.png"
cv2.imwrite(out_path, out_img)
print(f"Saved to {out_path}")
