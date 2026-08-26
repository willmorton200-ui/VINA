"""
Исправленная диагностика: Castillo de Liria
Нижний эллипс ОБЯЗАН "улыбаться" (прогиб ВНИЗ, delta > 0) по закону перспективы цилиндра.
Точки пересечения эллипсов с боковыми касательными — это истинные угловые точки.
"""
import cv2
import numpy as np
import os
from pipeline.stage1_preprocessing import Stage1Preprocessor

img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"
img_bgr = cv2.imread(img_path)
p1 = Stage1Preprocessor()
crop_bgr, crop_mask, bbox_info = p1.segment_bottle_and_label(img_bgr)
h, w = crop_mask.shape[:2]

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
mask_closed = cv2.morphologyEx(crop_mask, cv2.MORPH_CLOSE, kernel)

y_indices, x_indices = np.where(mask_closed > 127)
valid_ys = np.unique(y_indices)
left_wall = []
right_wall = []
for y in valid_ys:
    col_xs = np.where(mask_closed[y, :] > 127)[0]
    if len(col_xs) > 0:
        left_wall.append((float(col_xs[0]), float(y)))
        right_wall.append((float(col_xs[-1]), float(y)))
left_wall = np.array(left_wall)
right_wall = np.array(right_wall)

y_min, y_max = int(np.min(y_indices)), int(np.max(y_indices))
H_mask = y_max - y_min

# ========================================================================
# ШАГ 2: Касательные к боковым граням (регрессия по центральным 60%)
# ========================================================================
y_lo = y_min + 0.20 * H_mask
y_hi = y_min + 0.80 * H_mask

L_filt = left_wall[(left_wall[:, 1] >= y_lo) & (left_wall[:, 1] <= y_hi)]
poly_L = np.polyfit(L_filt[:, 1], L_filt[:, 0], deg=1)
theta_L_deg = np.degrees(np.arctan(poly_L[0]))

R_filt = right_wall[(right_wall[:, 1] >= y_lo) & (right_wall[:, 1] <= y_hi)]
poly_R = np.polyfit(R_filt[:, 1], R_filt[:, 0], deg=1)
theta_R_deg = np.degrees(np.arctan(poly_R[0]))

print(f"Левая касательная: угол = {theta_L_deg:.2f}°")
print(f"Правая касательная: угол = {theta_R_deg:.2f}°")

y_range = np.linspace(y_min, y_max, 200)
L_tangent_x = np.polyval(poly_L, y_range)
R_tangent_x = np.polyval(poly_R, y_range)

# ========================================================================
# ШАГ 3: Полуэллипсы по верхнему и нижнему контуру
# ========================================================================
N_pts = 80

# --- Верхний профиль ---
# Используем касательные для определения x-диапазона на высоте верхнего ряда маски
# P_TL определяется пересечением левой касательной с верхним рядом маски
# P_TR - пересечением правой касательной с верхним рядом маски

# Сначала найдём верхний и нижний y границы этикетки по маске
# Верхний срез: первые 10% строк, найти устойчивый y_top
top_10_pct = left_wall[left_wall[:, 1] <= y_min + 0.10 * H_mask]
y_top_stable = float(np.median(top_10_pct[:, 1])) if len(top_10_pct) > 5 else float(y_min)

bot_10_pct = left_wall[left_wall[:, 1] >= y_max - 0.10 * H_mask]
y_bot_stable = float(np.median(bot_10_pct[:, 1])) if len(bot_10_pct) > 5 else float(y_max)

# Угловые точки через пересечение касательных с y_top и y_bot
P_TL = np.array([np.polyval(poly_L, y_top_stable), y_top_stable])
P_TR = np.array([np.polyval(poly_R, y_top_stable), y_top_stable])
P_BL = np.array([np.polyval(poly_L, y_bot_stable), y_bot_stable])
P_BR = np.array([np.polyval(poly_R, y_bot_stable), y_bot_stable])

print(f"P_TL={P_TL}, P_TR={P_TR}")
print(f"P_BL={P_BL}, P_BR={P_BR}")

W_top = abs(P_TR[0] - P_TL[0])
W_bot = abs(P_BR[0] - P_BL[0])
label_H = abs(P_BL[1] - P_TL[1])

# --- Верхний профиль маски ---
xs_top = np.linspace(P_TL[0], P_TR[0], N_pts)
raw_ys_top = []
for x in xs_top:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask_closed[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_top.append(float(np.min(col_ys)))
    else:
        raw_ys_top.append(P_TL[1])
raw_ys_top = np.array(raw_ys_top)

# Медианная стрела прогиба верха по центральным 30%
mid_idx = N_pts // 2
mid_span = max(1, int(N_pts * 0.15))
y_mid_top = float(np.median(raw_ys_top[mid_idx - mid_span : mid_idx + mid_span]))
y_corners_top = (P_TL[1] + P_TR[1]) / 2.0
delta_top = y_mid_top - y_corners_top  # + = smile (вниз), - = frown (вверх)
a_top = W_top / 2.0
e_top = delta_top / a_top

print(f"\nВерхний полуэллипс: delta_top = {delta_top:.1f}px, a_top = {a_top:.1f}px, e_top = {e_top:.3f}")

# --- Нижний профиль маски ---
xs_bot = np.linspace(P_BL[0], P_BR[0], N_pts)
raw_ys_bot = []
for x in xs_bot:
    x_int = int(np.clip(round(x), 0, w - 1))
    col_ys = np.where(mask_closed[:, x_int] > 127)[0]
    if len(col_ys) > 0:
        raw_ys_bot.append(float(np.max(col_ys)))
    else:
        raw_ys_bot.append(P_BL[1])
raw_ys_bot = np.array(raw_ys_bot)

y_mid_bot = float(np.median(raw_ys_bot[mid_idx - mid_span : mid_idx + mid_span]))
y_corners_bot = (P_BL[1] + P_BR[1]) / 2.0
delta_bot_raw = y_mid_bot - y_corners_bot
a_bot = W_bot / 2.0

print(f"Нижний сырой: delta_bot_raw = {delta_bot_raw:.1f}px (сырой из маски)")

# ЗАКОН ПЕРСПЕКТИВЫ: Нижний эллипс ОБЯЗАН "улыбаться" (delta > 0)
# когда верхний тоже "улыбается" (delta_top > 0, камера сверху).
# Применяем закон раскрываемости с коэффициентом 3x (kappa = 0.255):
aspect_hw = label_H / max(W_top + W_bot, 1.0) * 2.0
e_bot_perspective = e_top + aspect_hw * 0.255
delta_bot_perspective = e_bot_perspective * a_bot

# Нижняя дуга ВСЕГДА берётся как максимум между сырым и перспективным
if delta_top >= 0:
    delta_bot = max(delta_bot_raw, delta_bot_perspective)
else:
    delta_bot = delta_bot_raw

print(f"Нижний перспективный: e_bot = {e_bot_perspective:.3f}, delta_bot_perspective = {delta_bot_perspective:.1f}px")
print(f"Итоговый delta_bot = {delta_bot:.1f}px (SMILE ↓)")

# ========================================================================
# Построение эллипсоидных кривых
# ========================================================================
theta = np.linspace(0.0, np.pi, N_pts)

# Верхний полуэллипс
x0_top = (P_TL[0] + P_TR[0]) / 2.0
T_ell_x = x0_top - a_top * np.cos(theta)
tilt_top = (1.0 - theta / np.pi) * P_TL[1] + (theta / np.pi) * P_TR[1] - y_corners_top
T_ell_y = y_corners_top + delta_top * np.sin(theta) + tilt_top
T_ell_y[0], T_ell_y[-1] = P_TL[1], P_TR[1]
T_curve = np.column_stack((T_ell_x, T_ell_y))

# Нижний полуэллипс (SMILE! delta_bot > 0 => прогиб ВНИЗ)
x0_bot = (P_BL[0] + P_BR[0]) / 2.0
B_ell_x = x0_bot - a_bot * np.cos(theta)
tilt_bot = (1.0 - theta / np.pi) * P_BL[1] + (theta / np.pi) * P_BR[1] - y_corners_bot
B_ell_y = y_corners_bot + delta_bot * np.sin(theta) + tilt_bot
B_ell_y[0], B_ell_y[-1] = P_BL[1], P_BR[1]
B_curve = np.column_stack((B_ell_x, B_ell_y))

# ========================================================================
# Точки пересечения эллипсов с боковыми касательными
# ========================================================================
def find_ellipse_tangent_intersection(ell_curve, poly_tan, side="left"):
    """Находит точку пересечения эллипса с прямой x = m*y + c"""
    min_dist = 1e9
    best_pt = ell_curve[0] if side == "left" else ell_curve[-1]
    for pt in ell_curve:
        x_on_tangent = np.polyval(poly_tan, pt[1])
        d = abs(pt[0] - x_on_tangent)
        if d < min_dist:
            min_dist = d
            best_pt = pt.copy()
    return best_pt

P_TL_int = find_ellipse_tangent_intersection(T_curve, poly_L, "left")
P_TR_int = find_ellipse_tangent_intersection(T_curve, poly_R, "right")
P_BL_int = find_ellipse_tangent_intersection(B_curve, poly_L, "left")
P_BR_int = find_ellipse_tangent_intersection(B_curve, poly_R, "right")

print(f"\nТочки пересечения (эллипс × касательная):")
print(f"  P_TL = [{P_TL_int[0]:.1f}, {P_TL_int[1]:.1f}]")
print(f"  P_TR = [{P_TR_int[0]:.1f}, {P_TR_int[1]:.1f}]")
print(f"  P_BL = [{P_BL_int[0]:.1f}, {P_BL_int[1]:.1f}]")
print(f"  P_BR = [{P_BR_int[0]:.1f}, {P_BR_int[1]:.1f}]")

# ========================================================================
# ВИЗУАЛИЗАЦИЯ
# ========================================================================
artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"

vis = crop_bgr.copy()
mask_2d = crop_mask > 127
green_layer = crop_bgr.copy()
green_layer[mask_2d] = [40, 225, 60]
vis[mask_2d] = cv2.addWeighted(crop_bgr[mask_2d], 0.6, green_layer[mask_2d], 0.4, 0)

# Сырые точки контура маски (мелкие серые точки)
for pt in left_wall[::4]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 2, (180, 180, 180), -1)
for pt in right_wall[::4]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 2, (180, 180, 180), -1)

# Касательные к бокам (жёлтые прямые)
for i in range(len(y_range) - 1):
    cv2.line(vis,
             (int(L_tangent_x[i]), int(y_range[i])),
             (int(L_tangent_x[i+1]), int(y_range[i+1])),
             (0, 255, 255), 3, cv2.LINE_AA)
    cv2.line(vis,
             (int(R_tangent_x[i]), int(y_range[i])),
             (int(R_tangent_x[i+1]), int(y_range[i+1])),
             (0, 255, 255), 3, cv2.LINE_AA)

# Верхний эллипс (зелёный)
cv2.polylines(vis, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

# Нижний эллипс SMILE (зелёный, прогиб ВНИЗ)
cv2.polylines(vis, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)

# Сырой нижний профиль маски (красный пунктир для сравнения)
for i in range(len(xs_bot)):
    cv2.circle(vis, (int(xs_bot[i]), int(raw_ys_bot[i])), 2, (0, 0, 255), -1)

# Точки пересечения (большие зелёные кружки)
for pt in [P_TL_int, P_TR_int, P_BL_int, P_BR_int]:
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 11, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 9, (0, 255, 0), -1, cv2.LINE_AA)
    cv2.circle(vis, (int(pt[0]), int(pt[1])), 4, (255, 255, 255), -1, cv2.LINE_AA)

cv2.imwrite(os.path.join(artifacts_dir, "castillo_smile_corrected.png"), vis)
print("\nСохранено: castillo_smile_corrected.png")
