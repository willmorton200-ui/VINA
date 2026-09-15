import cv2
import numpy as np
import os

artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\982dbb9e-4780-4467-a511-0a784bef8b97"

def make_pipeline_board(prefix, title):
    imgs = [
        ("1. Исходный кроп", cv2.imread(os.path.join(artifacts_dir, f"{prefix}_step1_crop.png"))),
        ("2. Маска SAM + Габариты", cv2.imread(os.path.join(artifacts_dir, f"{prefix}_step2_mask.png"))),
        ("3. Боковые вектора и 4 точки", cv2.imread(os.path.join(artifacts_dir, f"{prefix}_step3_vectors.png"))),
        ("4. Верхняя и нижняя кривые", cv2.imread(os.path.join(artifacts_dir, f"{prefix}_step4_curves.png"))),
        ("5. Наложение 3D сетки", cv2.imread(os.path.join(artifacts_dir, f"{prefix}_step5_3d_mesh.png"))),
        ("6. Финальная развертка", cv2.imread(os.path.join(artifacts_dir, f"{prefix}_step6_dewarped.png"))),
    ]
    
    target_h = 420
    resized = []
    for label, im in imgs:
        if im is None:
            continue
        h, w = im.shape[:2]
        scale = target_h / float(h)
        new_w = int(w * scale)
        r = cv2.resize(im, (new_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        
        # Header banner
        banner = np.zeros((45, new_w, 3), dtype=np.uint8) + 30
        cv2.putText(banner, label, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)
        card = np.vstack((banner, r))
        # Add border
        card = cv2.copyMakeBorder(card, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=[80, 80, 80])
        resized.append(card)
        
    # Split into 2 rows of 3 images
    row1 = np.hstack(resized[:3])
    row2 = np.hstack(resized[3:])
    
    # Pad rows to same width if slightly different
    w1, w2 = row1.shape[1], row2.shape[1]
    max_w = max(w1, w2)
    if w1 < max_w:
        row1 = cv2.copyMakeBorder(row1, 0, 0, 0, max_w - w1, cv2.BORDER_CONSTANT, value=[30, 30, 30])
    if w2 < max_w:
        row2 = cv2.copyMakeBorder(row2, 0, 0, 0, max_w - w2, cv2.BORDER_CONSTANT, value=[30, 30, 30])
        
    board = np.vstack((row1, row2))
    
    # Title header
    top_title = np.zeros((65, max_w, 3), dtype=np.uint8) + 20
    cv2.putText(top_title, f"VINA v1.2 Pipeline: {title}", (20, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (255, 255, 255), 2, cv2.LINE_AA)
    final_board = np.vstack((top_title, board))
    
    out_path = os.path.join(artifacts_dir, f"{prefix}_pipeline_board_v12.png")
    cv2.imwrite(out_path, final_board)
    print(f"Saved: {out_path}")

make_pipeline_board("castillo_white", "Castillo de Liria (Sauvignon Blanc Viura)")
make_pipeline_board("castillo_red", "Castillo de Liria (Monastrell Medium Sweet)")
