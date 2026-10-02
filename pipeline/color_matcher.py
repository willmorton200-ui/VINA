import cv2
import numpy as np

# 7 базовых цветов (в формате BGR)
BASIC_COLORS = {
    "red": (0, 0, 255),
    "orange": (0, 165, 255),
    "yellow": (0, 255, 255),
    "green": (0, 255, 0),
    "blue": (255, 0, 0),
    "purple": (128, 0, 128),
    "white_or_light": (240, 240, 240),
    "black_or_dark": (20, 20, 20)
}

def get_dominant_color_name(image_bgr: np.ndarray, crop_center: bool = True) -> str:
    """
    Вычисляет доминирующий цвет на изображении (или в его центре).
    Если в центре более 4 значимых цветов, берется средний цвет (колорит),
    иначе берется доминирующий. Затем цвет приводится к базовой гамме.
    """
    if image_bgr is None or image_bgr.size == 0:
        return "unknown"
        
    if crop_center:
        h, w = image_bgr.shape[:2]
        # Берем центральную 1/5 (20%) изображения
        y1, y2 = int(h * 0.4), int(h * 0.6)
        x1, x2 = int(w * 0.4), int(w * 0.6)
        if y2 > y1 and x2 > x1:
            image_bgr = image_bgr[y1:y2, x1:x2]
        
    # Сжимаем для скорости
    h, w = image_bgr.shape[:2]
    scale = 64.0 / max(h, w)
    if scale < 1.0:
        img = cv2.resize(image_bgr, (0,0), fx=scale, fy=scale)
    else:
        img = image_bgr.copy()
        
    pixels = img.reshape((-1, 3)).astype(np.float32)
    
    if len(pixels) == 0:
        return "unknown"

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    try:
        # Пробуем выделить 5 кластеров
        _, labels, centers = cv2.kmeans(pixels, 5, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        counts = np.bincount(labels.flatten())
        
        # Считаем значимыми цвета, занимающие > 5% площади
        total_pixels = len(pixels)
        significant_colors = np.sum((counts / total_pixels) > 0.05)
        
        if significant_colors > 4:
            # Более 4 цветов -> пестрая наклейка, берем колорит (средний цвет)
            dominant_bgr = np.mean(pixels, axis=0)
        else:
            # 1-4 цвета -> берем доминирующий (самый частый)
            dominant_bgr = centers[np.argmax(counts)]
    except Exception:
        dominant_bgr = np.mean(pixels, axis=0)

    # Ищем ближайший из базовых цветов
    best_name = "unknown"
    min_dist = float('inf')
    
    for name, bgr in BASIC_COLORS.items():
        # Евклидово расстояние в RGB пространстве
        dist = np.linalg.norm(dominant_bgr - np.array(bgr))
        if dist < min_dist:
            min_dist = dist
            best_name = name
            
    return best_name

def calculate_color_bonus(label_bgr: np.ndarray, catalog_wine_color: str) -> float:
    """
    Возвращает бонус (или штраф) к confidence в зависимости от совпадения
    цвета этикетки и цвета вина из каталога.
    """
    if not catalog_wine_color or not isinstance(catalog_wine_color, str):
        return 0.0
        
    catalog_color = catalog_wine_color.lower().strip()
    detected_color = get_dominant_color_name(label_bgr)
    
    bonus = 0.0
    
    # Логика соответствия
    if "бел" in catalog_color:
        if detected_color in ["white_or_light", "yellow", "green"]:
            bonus = 5.0  # Логичное совпадение
        elif detected_color in ["red", "purple", "black_or_dark"]:
            bonus = -5.0 # Противоречие
            
    elif "красн" in catalog_color:
        if detected_color in ["red", "purple", "black_or_dark"]:
            bonus = 5.0
        elif detected_color in ["white_or_light", "yellow", "green", "blue"]:
            bonus = -5.0
            
    elif "роз" in catalog_color:
        if detected_color in ["red", "white_or_light", "purple", "orange"]:
            bonus = 3.0
            
    elif "оранж" in catalog_color:
        if detected_color in ["orange", "yellow"]:
            bonus = 5.0

    return bonus

def calculate_visual_color_bonus(query_bgr: np.ndarray, ref_bgr: np.ndarray) -> float:
    """
    Сравнивает визуальные цвета центра двух наклеек (с фото и из базы).
    """
    if query_bgr is None or ref_bgr is None:
        return 0.0
        
    query_color = get_dominant_color_name(query_bgr, crop_center=True)
    ref_color = get_dominant_color_name(ref_bgr, crop_center=True)
    
    if query_color == "unknown" or ref_color == "unknown":
        return 0.0
        
    if query_color == ref_color:
        return 5.0  # Точное совпадение спектра
        
    # Проверка на родственные цвета
    light_colors = {"white_or_light", "yellow", "orange", "green"}
    dark_colors = {"black_or_dark", "purple", "blue", "red"}
    
    if (query_color in light_colors and ref_color in light_colors) or \
       (query_color in dark_colors and ref_color in dark_colors):
        return 3.0  # Схожий спектр (оба светлые или оба темные)
        
    # Противоречие
    return -5.0

def calculate_structural_orb_matches(query_img: np.ndarray, ref_bgr: np.ndarray) -> int:
    """
    Выполняет структурное сравнение двух изображений с помощью ORB (Oriented FAST and Rotated BRIEF).
    Возвращает количество "хороших" совпадений ключевых точек.
    Используется как надежный тай-брейк для различения почти идентичных этикеток.
    """
    if query_img is None or ref_bgr is None:
        return 0
        
    try:
        # Конвертируем в градации серого, если необходимо
        if len(query_img.shape) == 3:
            q_gray = cv2.cvtColor(query_img, cv2.COLOR_BGR2GRAY)
        else:
            q_gray = query_img
            
        if len(ref_bgr.shape) == 3:
            r_gray = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
        else:
            r_gray = ref_bgr
            
        orb = cv2.ORB_create(nfeatures=1000)
        kp1, des1 = orb.detectAndCompute(q_gray, None)
        kp2, des2 = orb.detectAndCompute(r_gray, None)
        
        if des1 is None or des2 is None:
            return 0
            
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        
        # Считаем "хорошими" совпадения с дистанцией < 50
        good_matches = sum(1 for m in matches if m.distance < 50)
        return good_matches
    except Exception as e:
        print(f"[ORB Matcher] Error: {e}")
        return 0
