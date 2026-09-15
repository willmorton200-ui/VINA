import cv2
import numpy as np
import os
import json

from pipeline.multi_label_engine import MultiLabelBottleEngine

engine = MultiLabelBottleEngine(use_gpu=True)

test_images = [
    ("Barakiani", "test_dataset/butilki/photo_2026-08-10_12-34-31.jpg"),
    ("Castillo_White", "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"),
    ("Michel_Schneider", "test_dataset/butilki/photo_2026-08-10_12-34-30.jpg")
]

for name, img_path in test_images:
    print(f"\n=======================================================")
    print(f"Testing Multi-Label Engine on: {name} ({img_path})")
    print(f"=======================================================")
    
    img = cv2.imread(img_path)
    bottles = engine.process_image(img)
    
    print(f"Detected {len(bottles)} bottle(s) in photo.")
    for b in bottles:
        print(f"\n--- [Бутылка #{b.bottle_id}] BBox: {b.bottle_bbox} ---")
        print(f"Количество найденных этикеток: {len(b.labels)}")
        print(f"Общий статус трансформации: {b.overall_status}")
        print(f"Слов до развертки (Raw): {b.total_raw_words} | Слов после (Dewarped): {b.total_dewarped_words} (Прирост: {b.total_gain_words:+d})")
        
        print("\nПорядок этикеток (Сверху Вниз):")
        for lbl in b.labels:
            print(f"  [{lbl.label_id}] {lbl.label_type:22s} | Угол биссектрисы: {lbl.bisector_angle_deg:+.2f}° | Статус: {lbl.transformation_status}")
            print(f"      Raw OCR ({len(lbl.raw_ocr['text_blocks'])} сл):      {lbl.raw_ocr['full_text']}")
            print(f"      Dewarped OCR ({len(lbl.dewarped_ocr['text_blocks'])} сл): {lbl.dewarped_ocr['full_text']}")
            
        print("\nСводный распознанный текст бутылки (Top-to-Bottom):")
        print(b.consolidated_text)
