import os
import glob
import cv2
import numpy as np
import shutil
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

UPLOADS_DIR = r"D:\VINA\TZ\Датасет\Датасет\prod-svoe-vino-strapi\prod-svoe-vino\strapi\uploads"
BACKUP_DIR = r"D:\VINA\TZ\Датасет\Датасет\prod-svoe-vino-strapi\prod-svoe-vino\strapi\uploads_backup"

def process_image(filepath):
    # Read the image
    # cv2.imread might fail with Cyrillic paths, so we use numpy
    with open(filepath, "rb") as f:
        bytes = bytearray(f.read())
    nparray = np.asarray(bytes, dtype=np.uint8)
    img = cv2.imdecode(nparray, cv2.IMREAD_UNCHANGED)
    
    if img is None:
        return False

    # If already has 4 channels, and some pixels are transparent, we can skip or re-process
    # But let's force re-process to remove black just in case
    if len(img.shape) == 3 and img.shape[2] == 4:
        # Convert to BGR for processing
        bgr = img[:, :, :3]
    else:
        bgr = img

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    
    # Threshold to find non-black pixels
    # Since black is 0, any pixel > 8 is considered foreground
    # This leaves a bit of margin for compression artifacts
    _, thresh = cv2.threshold(gray, 8, 255, cv2.THRESH_BINARY)
    
    # Morphological operations to clean up noise and fill holes in the bottle
    kernel = np.ones((5,5), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
    
    # Find the largest contour (the bottle)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return False
        
    c = max(contours, key=cv2.contourArea)
    
    # Create the alpha mask
    alpha = np.zeros_like(gray)
    cv2.drawContours(alpha, [c], -1, 255, -1)
    
    # Add slightly blurred edges to avoid jagged aliasing
    alpha = cv2.GaussianBlur(alpha, (3,3), 0)
    
    # Merge into BGRA
    b, g, r = cv2.split(bgr)
    bgra = cv2.merge((b, g, r, alpha))
    
    # Save back to webp
    success, encoded = cv2.imencode('.webp', bgra)
    if success:
        with open(filepath, "wb") as f:
            f.write(encoded)
        return True
    return False

def main():
    print("Создаем резервную копию папки uploads (это может занять время)...")
    if not os.path.exists(BACKUP_DIR):
        shutil.copytree(UPLOADS_DIR, BACKUP_DIR)
        print("Резервная копия создана в:", BACKUP_DIR)
    else:
        print("Резервная копия уже существует:", BACKUP_DIR)
        
    files = glob.glob(os.path.join(UPLOADS_DIR, "*.webp"))
    print(f"Найдено {len(files)} .webp файлов для обработки.")
    
    success_count = 0
    # Use ThreadPoolExecutor for speed
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(tqdm(executor.map(process_image, files), total=len(files), desc="Обработка картинок"))
        
    success_count = sum(1 for r in results if r)
    print(f"Успешно обработано {success_count} из {len(files)} файлов.")

if __name__ == "__main__":
    main()
