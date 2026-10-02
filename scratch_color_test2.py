import cv2
from pipeline.color_matcher import get_dominant_color_name, calculate_visual_color_bonus
from pipeline import CylindricalDewarpEngine

engine = CylindricalDewarpEngine(use_gpu=True)
img = cv2.imread(r"D:\VINA\owner_eval\1\queries\e3f116c0.jpeg")
res = engine.process_image(img)
dewarped_img = res.get("dewarped_bgr")

print("Dewarped shape:", dewarped_img.shape if dewarped_img is not None else None)

color = get_dominant_color_name(dewarped_img, crop_center=True)
print("Dewarped Color:", color)

ref_img = cv2.imread(r"D:\VINA\wines_images_clean\wines_images\vinodelnya-byurne-merlo-krasnoe-suhoe-14.webp")
ref_color = get_dominant_color_name(ref_img, crop_center=True)
print("Ref Color:", ref_color)

bonus = calculate_visual_color_bonus(dewarped_img, ref_img)
print("Bonus:", bonus)
