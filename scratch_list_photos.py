import cv2
import glob

for f in sorted(glob.glob("test_dataset/butilki/photo_2026-08-11_*.jpg")):
    img = cv2.imread(f)
    print(f"File: {f}, shape: {img.shape}")
