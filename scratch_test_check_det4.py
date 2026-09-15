import cv2
import numpy as np
from pipeline.stage1_preprocessing import Stage1Preprocessor

img_path = "d:/VINA/test_dataset/butilki/castillo_liria_pair.jpg"
img_bgr = cv2.imread(img_path)
H, W = img_bgr.shape[:2]

stage1 = Stage1Preprocessor(use_gpu=True)
yolo_res = stage1.yolo_model.predict(img_bgr, verbose=False, device=stage1.device, conf=0.20)
masks_data = yolo_res[0].masks.data.cpu().numpy()
boxes = yolo_res[0].boxes.xyxy.cpu().numpy()

for idx, box in enumerate(boxes):
    bx1, by1, bx2, by2 = [int(v) for v in box]
    m_raw = masks_data[idx]
    m_full = (cv2.resize(m_raw, (W, H)) > 0.5).astype(np.uint8) * 255
    m_clean = stage1._keep_largest_component(m_full)
    
    top = np.count_nonzero(m_clean[:4, :])
    bot = np.count_nonzero(m_clean[H-4:, :])
    left = np.count_nonzero(m_clean[:, :4])
    right = np.count_nonzero(m_clean[:, W-4:])
    tot = top + bot + left + right
    area = np.count_nonzero(m_clean)
    print(f"Det {idx}: box={[bx1, by1, bx2, by2]}, area={area}, border_contact={tot} (top={top}, bot={bot}, left={left}, right={right})")
