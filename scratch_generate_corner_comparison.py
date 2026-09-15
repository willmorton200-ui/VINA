import cv2
import numpy as np
import os

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"

def make_comparison_card(name, old_img_name, new_img_name, title):
    old_im = cv2.imread(os.path.join(artifacts_dir, old_img_name))
    new_im = cv2.imread(os.path.join(artifacts_dir, new_img_name))
    
    h = 520
    w_old = int(old_im.shape[1] * (h / float(old_im.shape[0])))
    w_new = int(new_im.shape[1] * (h / float(new_im.shape[0])))
    
    old_r = cv2.resize(old_im, (w_old, h), interpolation=cv2.INTER_LANCZOS4)
    new_r = cv2.resize(new_im, (w_new, h), interpolation=cv2.INTER_LANCZOS4)
    
    # Banners
    b_old = np.zeros((45, w_old, 3), dtype=np.uint8) + 30
    cv2.putText(b_old, "БЫЛО: Ошибка среза Y (смещены углы)", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
    card_old = np.vstack((b_old, old_r))
    
    b_new = np.zeros((45, w_new, 3), dtype=np.uint8) + 30
    cv2.putText(b_new, "СТАЛО: Точные точки отрыва образующих", (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
    card_new = np.vstack((b_new, new_r))
    
    combined = np.hstack((card_old, card_new))
    header = np.zeros((55, combined.shape[1], 3), dtype=np.uint8) + 20
    cv2.putText(header, f"Сравнение точности углов: {title}", (20, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    
    final_card = np.vstack((header, combined))
    out_path = os.path.join(artifacts_dir, f"{name}_corner_comparison.png")
    cv2.imwrite(out_path, final_card)
    print(f"Saved: {out_path}")

make_comparison_card("white", "castillo_white_step5_3d_mesh.png", "white_perfect_corners.png", "Белая бутылка (Castillo Sauvignon Blanc)")
make_comparison_card("red", "castillo_red_step5_3d_mesh.png", "red_perfect_corners.png", "Красная бутылка (Castillo Monastrell)")
