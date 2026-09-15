import cv2
import numpy as np
import os
from PIL import Image as PILImage, ImageDraw, ImageFont

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"
os.makedirs(artifacts_dir, exist_ok=True)

# Helper function to draw Cyrillic labels
def draw_cyrillic(img_bgr, text, org, font_size=18, text_color=(255, 255, 255), bg_color=None):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    pil_img = PILImage.fromarray(img_rgb)
    draw = ImageDraw.Draw(pil_img)
    font_path = r"C:\Windows\Fonts\arialbd.ttf"
    if not os.path.exists(font_path):
        font_path = r"C:\Windows\Fonts\arial.ttf"
    font = ImageFont.truetype(font_path, font_size)
    if bg_color is not None:
        bbox = draw.textbbox(org, text, font=font)
        draw.rectangle(bbox, fill=bg_color)
    draw.text(org, text, font=font, fill=text_color)
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

# Load test bottle: Barakiani
img_path = r"test_dataset/butilki/photo_2026-08-10_12-34-31.jpg"
img_bgr = cv2.imread(img_path)

from pipeline.stage1_preprocessing import Stage1Preprocessor
p1 = Stage1Preprocessor(use_gpu=True)

# Raw crop and mask (with holes in the middle, as is)
# Prompt covering the bottle label area
prompt_box = [235, 360, 675, 1120]
mask_raw, _ = p1.sam_refiner.refine_mask(img_bgr, prompt_box)

crop_bgr = img_bgr[340:1150, 220:700].copy()
mask_crop = mask_raw[340:1150, 220:700].copy()
h, w = crop_bgr.shape[:2]

# Ensure we retain the main mask component without touching internal holes
binary = np.uint8(mask_crop > 127) * 255
num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
if num_labels > 2:
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    clean_binary = np.zeros_like(binary)
    clean_binary[labels == largest_label] = 255
    binary = clean_binary

# =========================================================================
# STEP 1: ИГНОРИРОВАНИЕ ВНУТРЕННИХ ДЫР (ТОЛЬКО ВНЕШНИЙ КОНТУР)
# =========================================================================
contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cnt = max(contours, key=cv2.contourArea).squeeze(1)
N_cnt = len(cnt)

ys = cnt[:, 1]
xs = cnt[:, 0]
unique_ys = np.sort(np.unique(ys))

# Профиль левой и правой границ (только крайние внешние точки для каждого Y)
left_profile = []
right_profile = []
for y_cur in unique_ys:
    xs_at_y = cnt[cnt[:, 1] == y_cur, 0]
    left_profile.append([float(np.min(xs_at_y)), float(y_cur)])
    right_profile.append([float(np.max(xs_at_y)), float(y_cur)])
left_profile = np.array(left_profile)
right_profile = np.array(right_profile)

# =========================================================================
# STEP 2: ФИЛЬТРАЦИЯ РЕЗКИХ ПОРОГОВ И ВЫБРОСОВ НА БОКОВЫХ ГРАНЯХ
# =========================================================================
# Игнорируем резкие пороги: производная dx/dy на цилиндре плавная (|dx/dy| < 0.35)
y_min, y_max = np.min(ys), np.max(ys)
x_min, x_max = np.min(xs), np.max(xs)
H_mask = y_max - y_min

# Находим 4 угловые точки (точки перехода образующих в дуги):
# P_TL: крайняя левая точка в верхних 30%
cand_tl = left_profile[left_profile[:, 1] <= y_min + 0.30 * H_mask]
P_TL = cand_tl[np.argmin(cand_tl[:, 0])]

# P_TR: крайняя правая точка в верхних 30%
cand_tr = right_profile[right_profile[:, 1] <= y_min + 0.30 * H_mask]
P_TR = cand_tr[np.argmax(cand_tr[:, 0])]

# P_BL: точка излома левой границы при переходе в нижнюю дугу (зона 70-95%)
cand_bl = left_profile[(left_profile[:, 1] >= y_min + 0.70 * H_mask) & (left_profile[:, 1] <= y_min + 0.95 * H_mask)]
scores_bl = (cand_bl[:, 1] - y_min) - 0.6 * (cand_bl[:, 0] - x_min)
P_BL = cand_bl[np.argmax(scores_bl)]

# P_BR: точка излома правой границы при переходе в нижнюю дугу (зона 70-95%)
cand_br = right_profile[(right_profile[:, 1] >= y_min + 0.70 * H_mask) & (right_profile[:, 1] <= y_min + 0.95 * H_mask)]
scores_br = (cand_br[:, 1] - y_min) - 0.6 * (x_max - cand_br[:, 0])
P_BR = cand_br[np.argmax(scores_br)]

# =========================================================================
# STEP 3: ИЗВЛЕЧЕНИЕ 4-Х КРАЕВЫХ НАПРАВЛЯЮЩИХ (T, B, L, R)
# =========================================================================
def find_contour_idx(pt, cnt_pts):
    return int(np.argmin(np.hypot(cnt_pts[:, 0] - pt[0], cnt_pts[:, 1] - pt[1])))

i_tl = find_contour_idx(P_TL, cnt)
i_tr = find_contour_idx(P_TR, cnt)
i_bl = find_contour_idx(P_BL, cnt)
i_br = find_contour_idx(P_BR, cnt)

def get_segment(s_idx, e_idx):
    if (e_idx - s_idx) % N_cnt < (s_idx - e_idx) % N_cnt:
        return cnt[[(s_idx + i) % N_cnt for i in range((e_idx - s_idx) % N_cnt + 1)]]
    else:
        return cnt[[(s_idx - i) % N_cnt for i in range((s_idx - e_idx) % N_cnt + 1)]]

# Верхняя кривая T(u)
seg_t1 = get_segment(i_tl, i_tr)
seg_t2 = get_segment(i_tr, i_tl)
T_raw = seg_t1 if np.mean(seg_t1[:, 1]) < np.mean(seg_t2[:, 1]) else seg_t2
if T_raw[0, 0] > T_raw[-1, 0]: T_raw = T_raw[::-1]

# Нижняя дуга B(u)
seg_b1 = get_segment(i_bl, i_br)
seg_b2 = get_segment(i_br, i_bl)
B_raw = seg_b1 if np.mean(seg_b1[:, 1]) > np.mean(seg_b2[:, 1]) else seg_b2
if B_raw[0, 0] > B_raw[-1, 0]: B_raw = B_raw[::-1]

# Левая образующая L(v)
seg_l1 = get_segment(i_tl, i_bl)
seg_l2 = get_segment(i_bl, i_tl)
L_raw = seg_l1 if np.mean(seg_l1[:, 0]) < np.mean(seg_l2[:, 0]) else seg_l2
if L_raw[0, 1] > L_raw[-1, 1]: L_raw = L_raw[::-1]

# Правая образующая R(v)
seg_r1 = get_segment(i_tr, i_br)
seg_r2 = get_segment(i_br, i_tr)
R_raw = seg_r1 if np.mean(seg_r1[:, 0]) > np.mean(seg_r2[:, 0]) else seg_r2
if R_raw[0, 1] > R_raw[-1, 1]: R_raw = R_raw[::-1]

# Параметризация 60 узлами
N_pts = 60
u_vals = np.linspace(0.0, 1.0, N_pts)
v_vals = np.linspace(0.0, 1.0, N_pts)

T_curve = np.column_stack((np.interp(u_vals, np.linspace(0, 1, len(T_raw)), T_raw[:, 0]), np.interp(u_vals, np.linspace(0, 1, len(T_raw)), T_raw[:, 1])))
B_curve = np.column_stack((np.interp(u_vals, np.linspace(0, 1, len(B_raw)), B_raw[:, 0]), np.interp(u_vals, np.linspace(0, 1, len(B_raw)), B_raw[:, 1])))
L_curve = np.column_stack((np.interp(v_vals, np.linspace(0, 1, len(L_raw)), L_raw[:, 0]), np.interp(v_vals, np.linspace(0, 1, len(L_raw)), L_raw[:, 1])))
R_curve = np.column_stack((np.interp(v_vals, np.linspace(0, 1, len(R_raw)), R_raw[:, 0]), np.interp(v_vals, np.linspace(0, 1, len(R_raw)), R_raw[:, 1])))

# =========================================================================
# STEP 4: 3D СЕТКА COON'S PATCH S(u, v)
# =========================================================================
grid_rows, grid_cols = 24, 32
u_g = np.linspace(0.0, 1.0, grid_cols)
v_g = np.linspace(0.0, 1.0, grid_rows)

T_res = np.column_stack((np.interp(u_g, u_vals, T_curve[:, 0]), np.interp(u_g, u_vals, T_curve[:, 1])))
B_res = np.column_stack((np.interp(u_g, u_vals, B_curve[:, 0]), np.interp(u_g, u_vals, B_curve[:, 1])))
L_res = np.column_stack((np.interp(v_g, v_vals, L_curve[:, 0]), np.interp(v_g, v_vals, L_curve[:, 1])))
R_res = np.column_stack((np.interp(v_g, v_vals, R_curve[:, 0]), np.interp(v_g, v_vals, R_curve[:, 1])))

u_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)
v_grid = np.zeros((grid_rows, grid_cols), dtype=np.float32)

for i in range(grid_rows):
    v = v_g[i]
    for j in range(grid_cols):
        u = u_g[j]
        c_blend = (1.0 - u) * (1.0 - v) * P_TL + u * (1.0 - v) * P_TR + (1.0 - u) * v * P_BL + u * v * P_BR
        pt = (1.0 - v) * T_res[j] + v * B_res[j] + (1.0 - u) * L_res[i] + u * R_res[i] - c_blend
        u_grid[i, j] = np.clip(pt[0], 0, w - 1)
        v_grid[i, j] = np.clip(pt[1], 0, h - 1)

# =========================================================================
# ПОСТРОЕНИЕ НАГЛЯДНОЙ ВИЗУАЛИЗАЦИИ 4 ШАГОВ
# =========================================================================
# Шаг 1: Исходная готовая маска (с дырками в центре как есть)
vis1 = np.zeros_like(crop_bgr)
vis1[binary > 127] = [255, 255, 255]

# Шаг 2: Выделение внешнего контура и 4 углов (дырки игнорируются)
vis2 = vis1.copy()
cv2.drawContours(vis2, [cnt], -1, (0, 255, 255), 2, cv2.LINE_AA)
for pt, lbl in [(P_TL, "P_TL"), (P_TR, "P_TR"), (P_BL, "P_BL"), (P_BR, "P_BR")]:
    px, py = int(pt[0]), int(pt[1])
    cv2.circle(vis2, (px, py), 8, (255, 255, 255), -1, cv2.LINE_AA)
    cv2.circle(vis2, (px, py), 6, (0, 0, 255), -1, cv2.LINE_AA)
    vis2 = draw_cyrillic(vis2, lbl, (px + 8, py - 8), font_size=15, text_color=(0, 255, 255))

# Шаг 3: 4 Краевые направляющие T(u), B(u), L(v), R(v)
vis3 = crop_bgr.copy()
cv2.polylines(vis3, [L_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA) # Синий L(v)
cv2.polylines(vis3, [R_curve.astype(np.int32)], False, (255, 140, 0), 4, cv2.LINE_AA) # Синий R(v)
cv2.polylines(vis3, [T_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)   # Зеленый T(u)
cv2.polylines(vis3, [B_curve.astype(np.int32)], False, (0, 255, 0), 4, cv2.LINE_AA)   # Зеленый B(u)
for pt in [P_TL, P_TR, P_BL, P_BR]:
    cv2.circle(vis3, (int(pt[0]), int(pt[1])), 7, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.circle(vis3, (int(pt[0]), int(pt[1])), 2, (255, 255, 255), -1, cv2.LINE_AA)

# Шаг 4: 3D Сетка Coon's Patch на бутылке
vis4 = crop_bgr.copy()
cv2.polylines(vis4, [L_curve.astype(np.int32)], False, (255, 140, 0), 3, cv2.LINE_AA)
cv2.polylines(vis4, [R_curve.astype(np.int32)], False, (255, 140, 0), 3, cv2.LINE_AA)
cv2.polylines(vis4, [T_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
cv2.polylines(vis4, [B_curve.astype(np.int32)], False, (0, 255, 0), 3, cv2.LINE_AA)
for i in range(grid_rows):
    pts_row = np.column_stack((u_grid[i, :], v_grid[i, :])).astype(np.int32)
    cv2.polylines(vis4, [pts_row], False, (0, 230, 255), 1, cv2.LINE_AA)
for j in range(grid_cols):
    pts_col = np.column_stack((u_grid[:, j], v_grid[:, j])).astype(np.int32)
    cv2.polylines(vis4, [pts_col], False, (0, 180, 255), 1, cv2.LINE_AA)

# Сборка финального демонстрационного коллажа
h_card = 520
def scale_im(im):
    w_t = int(round(im.shape[1] * (h_card / float(im.shape[0]))))
    return cv2.resize(im, (w_t, h_card), interpolation=cv2.INTER_LANCZOS4)

def draw_banner(im, text, color):
    b = np.zeros((45, im.shape[1], 3), dtype=np.uint8) + 28
    b = draw_cyrillic(b, text, (10, 12), font_size=15, text_color=color)
    return np.vstack((b, im))

c1 = draw_banner(scale_im(vis1), "1. Готовая маска (как есть)", (255, 255, 255))
c2 = draw_banner(scale_im(vis2), "2. Внешний контур + 4 угла", (0, 255, 255))
c3 = draw_banner(scale_im(vis3), "3. Направляющие T, B, L, R", (0, 255, 0))
c4 = draw_banner(scale_im(vis4), "4. 3D Сетка Coon's Patch", (0, 200, 255))

row = np.hstack((c1, c2, c3, c4))
hdr = np.zeros((55, row.shape[1], 3), dtype=np.uint8) + 18
hdr = draw_cyrillic(hdr, "Построение направляющих по готовой маске (без изменения маски)", (20, 14), font_size=22, text_color=(255, 255, 255))
final_card = np.vstack((hdr, row))

out_path = os.path.join(artifacts_dir, "ready_mask_guide_extraction_demonstration.png")
cv2.imwrite(out_path, final_card)
print(f"Guide extraction demonstration saved: {out_path}")
