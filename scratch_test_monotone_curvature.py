import cv2
import numpy as np
import os
import matplotlib.pyplot as plt

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

# ========================================================================
# ПРАВИЛО ОДНОСТОРОННЕЙ ВОГНУТОСТИ С ПРИОРИТЕТОМ К КРАЯМ КРИВОЙ
# ========================================================================

def fit_monotone_curvature_guide(xs, raw_ys, P_left, P_right, preferred_direction="smile", N_pts=80):
    """
    Строит направляющую кривую со СТРОГО ОДНОСТОРОННЕЙ ВОГНУТОСТЬЮ:
    1. Исключает двойную кривизну (S-образность, центральные горбы/наплывы).
    2. Приоритет отдается краевым зонам кривой (первые и последние 25%), где маска надежно привязана к углам.
    3. Аналитически вписывает канонический полуэллипс цилиндра с постоянным знаком второй производной.
    """
    N = len(raw_ys)
    u_norm = np.linspace(0.0, 1.0, N)
    
    # 1. Весовая функция с приоритетом к краям (Edge-Priority Weights)
    # На краях вес w = 4.0, в центре w = 1.0
    edge_weights = 1.0 + 3.0 * (2.0 * u_norm - 1.0) ** 2
    
    # 2. Оценка саггиты (стрелы прогиба) по надежным краевым участкам (первые и последние 25%)
    edge_span = max(2, int(N * 0.25))
    
    # Левый и правый краевые наклоны
    y_corner_avg = (P_left[1] + P_right[1]) / 2.0
    tilt_linear = (1.0 - u_norm) * P_left[1] + u_norm * P_right[1]
    
    # Разница между сырым профилем маски и базовой наклонной прямой
    raw_delta = raw_ys - tilt_linear
    
    # Краевая стрела прогиба: на эллипсе y_delta(u) = delta * sin(pi * u)
    # На краях u in [0.05..0.25] и [0.75..0.95]: sin(pi*u) in [0.15..0.70]
    sin_vals = np.sin(np.pi * u_norm)
    valid_sin = sin_vals > 0.15
    
    # Оценка delta_fit взвешенным методом МНК с краевыми весами:
    # min sum w_i * (raw_delta_i - delta * sin_i)^2 => delta = sum(w*delta*sin) / sum(w*sin^2)
    # ИСКЛЮЧАЕМ центральные 40% (u in [0.30..0.70]), где образуются паразитные горбы/наплывы!
    edge_mask = (u_norm <= 0.30) | (u_norm >= 0.70)
    
    num = np.sum(edge_weights[edge_mask] * raw_delta[edge_mask] * sin_vals[edge_mask])
    den = np.sum(edge_weights[edge_mask] * (sin_vals[edge_mask] ** 2))
    
    delta_edge_fit = num / max(den, 1e-6)
    
    # 3. Фильтрация направления кривизны (правило односторонней вогнутости)
    if preferred_direction == "smile":
        # Кривая ОБЯЗАНА прогибаться строго вниз (delta >= 0)
        delta_final = max(delta_edge_fit, 5.0) # минимальный прогиб 5px для цилиндра
    elif preferred_direction == "frown":
        # Кривая прогибается строго вверх (delta <= 0)
        delta_final = min(delta_edge_fit, -5.0)
    else:
        delta_final = delta_edge_fit
        
    print(f"  [Fit Guide] Оценка саггиты по краям: delta = {delta_final:.1f} px (направление: {preferred_direction})")
    
    # 4. Построение идеального полуэллипса с постоянной кривизной
    theta = np.linspace(0.0, np.pi, N_pts)
    x0 = (P_left[0] + P_right[0]) / 2.0
    a = max(abs(P_right[0] - P_left[0]) / 2.0, 1.0)
    
    ell_x = x0 - a * np.cos(theta)
    tilt = (1.0 - theta / np.pi) * P_left[1] + (theta / np.pi) * P_right[1] - y_corner_avg
    ell_y = y_corner_avg + delta_final * np.sin(theta) + tilt
    ell_y[0] = P_left[1]
    ell_y[-1] = P_right[1]
    
    curve = np.column_stack((ell_x, ell_y))
    return curve, delta_final

# ========================================================================
# ПРИМЕНЕНИЕ НА CASTILLO DE LIRIA
# ========================================================================

# Опорные углы по боковым касательным
P_TL = np.array([69.5, 44.0])
P_TR = np.array([564.2, 54.0])
P_BL = np.array([24.0, 485.0])
P_BR = np.array([400.7, 535.0])

# 1. Извлечение сырого верхнего профиля маски (с паразитным центральным горбом)
N_pts = 80
xs_top = np.linspace(P_TL[0], P_TR[0], N_pts)
raw_ys_top = []
for x in xs_top:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(crop_mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_top.append(float(np.min(col_ys)))
    else:
        raw_ys_top.append(P_TL[1])
raw_ys_top = np.array(raw_ys_top)

# Вписывание верхней направляющей со СТРОГО ОДНОСТОРОННЕЙ ВОГНУТОСТЬЮ (SMILE)
T_clean_curve, delta_T = fit_monotone_curvature_guide(xs_top, raw_ys_top, P_TL, P_TR, preferred_direction="smile", N_pts=N_pts)

# 2. Извлечение сырого нижнего профиля маски
xs_bot = np.linspace(P_BL[0], P_BR[0], N_pts)
raw_ys_bot = []
for x in xs_bot:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(crop_mask[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_bot.append(float(np.max(col_ys)))
    else:
        raw_ys_bot.append(P_BL[1])
raw_ys_bot = np.array(raw_ys_bot)

# Вписывание нижней направляющей со СТРОГО ОДНОСТОРОННЕЙ ВОГНУТОСТЬЮ (SMILE)
B_clean_curve, delta_B = fit_monotone_curvature_guide(xs_bot, raw_ys_bot, P_BL, P_BR, preferred_direction="smile", N_pts=N_pts)

# ========================================================================
# ВИЗУАЛИЗАЦИЯ И СРАВНЕНИЕ КРИВИЗНЫ
# ========================================================================
artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"

vis = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.65, green_layer[mask_2d], 0.35, 0)

# Сырой верхний контур с горбом (Красный пунктир)
for i in range(len(xs_top)):
    cv2.circle(vis, (int(xs_top[i]), int(raw_ys_top[i])), 2, (0, 0, 255), -1)

# Идеальная кривая со строго односторонней вогнутостью (Ярко-зеленая)
cv2.polylines(vis, [T_clean_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)
cv2.polylines(vis, [B_clean_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

# Угловые точки
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 10, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA) # Красные кружки как на рисунке

cv2.imwrite(os.path.join(artifacts_dir, "castillo_monotone_curvature_overlay.png"), vis)

# График кривизны до и после
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

# 1. Профиль
ax = axes[0]
u_top = np.linspace(0, 1, len(raw_ys_top))
ax.plot(u_top, raw_ys_top, 'r-', linewidth=2, label='Сырая маска (с горбом в центре и двойной кривизной)')
ax.plot(u_top, T_clean_curve[:, 1], 'g-', linewidth=3, label='Правило односторонней вогнутости (краевой приоритет)')
ax.plot([0, 1], [P_TL[1], P_TR[1]], 'ro', markersize=8, label='Угловые точки P_TL, P_TR')
ax.set_title('Верхний профиль: Сырая маска vs Чистый полуэллипс', fontsize=12)
ax.set_ylabel('Y (пиксели)')
ax.legend()
ax.invert_yaxis()
ax.grid(True, alpha=0.3)

# 2. Вторая производная (Кривизна d2y/du2)
ax = axes[1]
d2y_raw = np.gradient(np.gradient(raw_ys_top, u_top), u_top)
d2y_clean = np.gradient(np.gradient(T_clean_curve[:, 1], u_top), u_top)

ax.plot(u_top, d2y_raw, 'r--', label='Кривизна сырой маски (меняет знак = ДВОЙНАЯ КРИВИЗНА)')
ax.plot(u_top, d2y_clean, 'g-', linewidth=2.5, label='Кривизна правила (СТРОГО ПОСТОЯННЫЙ ЗНАК)')
ax.axhline(0, color='k', linestyle=':', alpha=0.5)
ax.set_title('Вторая производная (d²y/du²): Проверка на двойную кривизну', fontsize=12)
ax.set_xlabel('Нормализованный X (0 → 1)')
ax.set_ylabel('d²y/du²')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(artifacts_dir, "castillo_monotone_curvature_graphs.png"), dpi=150)
plt.close()

print("\nSaved monotone curvature artifacts successfully!")
