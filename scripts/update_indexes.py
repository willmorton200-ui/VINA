#!/usr/bin/env python3
"""
Скрипт обновления FAISS индексов VINA (SigLIP2 + DINOv2-LoRA).
Находит в wines_integrated_clean.csv все вина с изображениями,
которых ещё нет в индексах models/siglip2_index.faiss и models/dino_all_wines_index.faiss,
вычисляет их эмбеддинги на GPU и добавляет в индекс.
"""

import os
import sys
import shutil
import pickle
import time
from pathlib import Path
import cv2
import faiss
import numpy as np
import torch
from PIL import Image

base_dir = Path(__file__).resolve().parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from pipeline.catalog import WineCatalog
from pipeline.search_engine import WineSearchEngine
from pipeline.dino_engine import DinoLabelEngine

def update_indexes():
    base_dir = Path(__file__).resolve().parent.parent
    models_dir = base_dir / "models"
    
    print("=" * 70)
    print("       ОБНОВЛЕНИЕ FAISS ИНДЕКСОВ VINA SCANNER")
    print("=" * 70)
    
    # 1. Загрузка каталога
    cat = WineCatalog()
    wines_with_images = cat.get_wines_with_images()
    print(f"\n[Каталог] Всего вин с изображениями в базе: {len(wines_with_images)}")
    
    # 2. Инициализация движков
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"[Device] Используется: {device}")
    
    print("\n[SigLIP2] Загрузка поискового движка SigLIP2...")
    search_engine = WineSearchEngine(cat, use_gpu=True)
    
    print("\n[DINOv2] Загрузка поискового движка DINOv2-LoRA...")
    dino_engine = DinoLabelEngine(cat, use_gpu=True)
    
    # 3. Бэкапы перед модификацией
    for p in [search_engine.index_path, search_engine.meta_path, str(dino_engine.index_path), str(dino_engine.meta_path)]:
        if os.path.exists(p):
            shutil.copy2(p, p + ".bak")
    print("\n[Резервные копии] Созданы файлы .bak для всех индексов.")
    
    # 4. Обновление SigLIP2
    current_sig_slugs = set(search_engine.slugs)
    missing_sig = [w for w in wines_with_images if w["slug"] not in current_sig_slugs]
    print(f"\n[SigLIP2] Найдено {len(missing_sig)} вин, отсутствующих в индексе.")
    
    if missing_sig:
        new_embs = []
        new_slugs = []
        for idx, wine in enumerate(missing_sig, 1):
            try:
                img = Image.open(wine["image_path"]).convert("RGB")
                emb = search_engine.get_embedding(img)
                new_embs.append(emb[0])
                new_slugs.append(wine["slug"])
                print(f"  + [{idx}/{len(missing_sig)}] SigLIP2: {wine['slug']}")
            except Exception as e:
                print(f"  ! Ошибка обработки {wine['slug']} ({wine['image_path']}): {e}")
                
        if new_embs:
            emb_matrix = np.vstack(new_embs).astype(np.float32)
            search_engine.index.add(emb_matrix)
            search_engine.slugs.extend(new_slugs)
            
            faiss.write_index(search_engine.index, search_engine.index_path)
            with open(search_engine.meta_path, "wb") as f:
                pickle.dump(search_engine.slugs, f)
            print(f"✓ [SigLIP2] Индекс обновлён: теперь {search_engine.index.ntotal} векторов.")
    else:
        print("✓ [SigLIP2] Все вина из каталога уже есть в индексе.")
        
    # 5. Обновление DINOv2
    current_dino_slugs = set(dino_engine.slugs)
    missing_dino = [w for w in wines_with_images if w["slug"] not in current_dino_slugs]
    print(f"\n[DINOv2] Найдено {len(missing_dino)} вин, отсутствующих в индексе.")
    
    if missing_dino:
        new_dino_embs = []
        new_dino_slugs = []
        for idx, wine in enumerate(missing_dino, 1):
            try:
                bgr = cv2.imread(wine["image_path"])
                if bgr is None:
                    pil = Image.open(wine["image_path"]).convert("RGB")
                    bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
                crop = dino_engine.crop_label(bgr)
                emb = dino_engine.embed_bgr([crop])
                new_dino_embs.append(emb[0])
                new_dino_slugs.append(wine["slug"])
                print(f"  + [{idx}/{len(missing_dino)}] DINOv2: {wine['slug']}")
            except Exception as e:
                print(f"  ! Ошибка DINO {wine['slug']}: {e}")
                
        if new_dino_embs:
            dino_matrix = np.vstack(new_dino_embs).astype(np.float32)
            dino_engine.index.add(dino_matrix)
            dino_engine.slugs.extend(new_dino_slugs)
            
            faiss.write_index(dino_engine.index, str(dino_engine.index_path))
            with open(dino_engine.meta_path, "wb") as f:
                pickle.dump(dino_engine.slugs, f)
            print(f"✓ [DINOv2] Индекс обновлён: теперь {dino_engine.index.ntotal} векторов.")
    else:
        print("✓ [DINOv2] Все вина из каталога уже есть в индексе.")
        
    # 6. Синхронизация с C:\test_vina (если существует)
    test_models = Path(r"C:\test_vina\models")
    if test_models.exists():
        print("\n[Синхронизация] Копирование обновлённых индексов в C:\\test_vina\\models...")
        for name in ["siglip2_index.faiss", "siglip2_index_meta.pkl", "dino_all_wines_index.faiss", "dino_all_wines_index_meta.pkl"]:
            src = models_dir / name
            dst = test_models / name
            if src.exists():
                shutil.copy2(src, dst)
                print(f"  → Скопирован {name}")
                
        # Также скопируем wines_integrated_clean.csv в C:\test_vina
        csv_src = base_dir / "wines_integrated_clean.csv"
        csv_dst = Path(r"C:\test_vina\wines_integrated_clean.csv")
        if csv_src.exists():
            shutil.copy2(csv_src, csv_dst)
            print("  → Скопирован wines_integrated_clean.csv")
            
    print("\n" + "=" * 70)
    print("✓ ВСЕ ИНДЕКСЫ УСПЕШНО ОБНОВЛЕНЫ!")
    print("=" * 70)

if __name__ == "__main__":
    update_indexes()
