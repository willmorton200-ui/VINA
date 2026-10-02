import cv2
import numpy as np
import os
from pipeline.color_matcher import get_dominant_color_name, calculate_visual_color_bonus

img_path = r"D:\VINA\owner_eval\1\queries\e3f116c0.jpeg"
img_bgr = cv2.imread(img_path)

ref_path = r"D:\VINA\wines_images_clean\wines_images\Merlo_2022_no_bg_preview_carve_photos_36278cfc22.webp"
ref_bgr = cv2.imread(ref_path)

print("Query Color:", get_dominant_color_name(img_bgr, crop_center=True))
print("Ref Color:", get_dominant_color_name(ref_bgr, crop_center=True))

penalty = calculate_visual_color_bonus(img_bgr, ref_bgr)
print(f"Bonus: {penalty}")
