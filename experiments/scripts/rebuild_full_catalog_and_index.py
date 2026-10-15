#!/usr/bin/env python3
"""
Скрипт переиндексации базы VINA Scanner на полную базу (2 037 вин, как в VINA2 / LCT2026).
Извлекает эмбеддинги SigLIP 2 (ViT-B-16-SigLIP2-384) с видеокарты RTX 3090 батчами,
индексируя как полный кадр бутылки (source.webp), так и кроп этикетки (label.webp)
для каждого вина, обеспечивая максимальную полноту и точность распознавания.
"""

import json
import os
import pickle
import time
from pathlib import Path
import faiss
import numpy as np
import open_clip
import pandas as pd
import torch
from PIL import Image


def main():
    print("=" * 80)
    print("      ПЕРЕИНДЕКСАЦИЯ БАЗЫ VINA SCANNER (ПОЛНАЯ БАЗА 2 037 ВИН)")
    print("=" * 80)

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"• Устройство: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    products_json_path = Path(r"D:\VINA\data\products_catalog.json")
    wines_csv_path = Path(r"D:\VINA\data\wines_integrated.csv")
    media_dir = Path(r"D:\VINA\media")
    models_dir = Path(r"D:\VINA\models")

    if not products_json_path.is_file():
        print(f"ОШИБКА: {products_json_path} не найден!", file=sys.stderr)
        return 1

    with open(products_json_path, "r", encoding="utf-8") as f:
        products = json.load(f)
    print(f"• Загружено товаров из products_catalog.json: {len(products)}")

    # Собираем список изображений для индексации
    # Для каждого товара берём:
    # 1. source.webp (каталожное фото бутылки)
    # 2. label.webp (эталонный кроп этикетки)
    items_to_index = []
    missing_files = 0

    for p in products:
        slug = p.get("slug")
        if not slug:
            continue

        prod_id = p.get("id")
        src_path = media_dir / "products" / prod_id / "source.webp"
        lbl_path = media_dir / "products" / prod_id / "label.webp"

        if src_path.is_file():
            items_to_index.append((str(src_path), slug, "source"))
        else:
            missing_files += 1

        if lbl_path.is_file():
            items_to_index.append((str(lbl_path), slug, "label"))
        else:
            missing_files += 1

    print(f"• Всего изображений для векторизации: {len(items_to_index)} (пропущено отсутствующих: {missing_files})")
    unique_slugs = len(set(x[1] for x in items_to_index))
    print(f"• Уникальных slug вин: {unique_slugs}")

    # Загрузка SigLIP 2
    model_name = "ViT-B-16-SigLIP2-384"
    pretrained = "webli"
    print(f"\n[1/3] Загрузка модели {model_name} ({pretrained}) в память GPU...")
    t0 = time.time()
    model, _, preprocess = open_clip.create_model_and_transforms(
        model_name,
        pretrained=pretrained,
        device=device,
    )
    model.eval()
    print(f"✓ Модель загружена за {time.time() - t0:.1f} с")

    # Батч-обработка изображений
    batch_size = 64
    print(f"\n[2/3] Векторизация {len(items_to_index)} изображений (batch_size={batch_size})...")
    t_start_enc = time.time()

    all_embeddings = []
    all_slugs = []

    for i in range(0, len(items_to_index), batch_size):
        batch_items = items_to_index[i : i + batch_size]
        batch_tensors = []
        valid_slugs = []

        for img_path, slug, kind in batch_items:
            try:
                with Image.open(img_path) as img:
                    img_rgb = img.convert("RGB")
                    tensor = preprocess(img_rgb)
                    batch_tensors.append(tensor)
                    valid_slugs.append(slug)
            except Exception as e:
                print(f"  Предупреждение: ошибка чтения {img_path}: {e}")

        if not batch_tensors:
            continue

        stacked = torch.stack(batch_tensors).to(device)
        with torch.no_grad(), torch.amp.autocast("cuda", enabled=(device.startswith("cuda"))):
            feats = model.encode_image(stacked)
            feats = feats / feats.norm(dim=-1, keepdim=True)
            emb_np = feats.cpu().numpy().astype(np.float32)

        all_embeddings.append(emb_np)
        all_slugs.extend(valid_slugs)

        done = min(i + batch_size, len(items_to_index))
        if done % 512 == 0 or done == len(items_to_index):
            elapsed = time.time() - t_start_enc
            fps = done / elapsed if elapsed > 0 else 0
            print(f"  Векторизовано {done}/{len(items_to_index)} ({fps:.1f} фото/сек)...")

    matrix = np.vstack(all_embeddings)
    dim = matrix.shape[1]
    total_vectors = matrix.shape[0]
    print(f"✓ Векторизация завершена за {time.time() - t_start_enc:.1f} с. Матрица: {total_vectors} x {dim}")

    # Построение FAISS индекса
    print(f"\n[3/3] Построение и сохранение FAISS IndexFlatIP...")
    index = faiss.IndexFlatIP(dim)
    index.add(matrix)
    print(f"✓ Индекс построен, векторов: {index.ntotal}")

    index_path = models_dir / "siglip2_index.faiss"
    meta_path = models_dir / "siglip2_index_meta.pkl"

    faiss.write_index(index, str(index_path))
    with open(meta_path, "wb") as f:
        pickle.dump(all_slugs, f)

    print(f"✓ Сохранён индекс: {index_path} ({index_path.stat().st_size / 1024 / 1024:.2f} МБ)")
    print(f"✓ Сохранён маппинг: {meta_path} ({meta_path.stat().st_size / 1024:.1f} КБ)")
    print("=" * 80)
    print(" ПЕРЕИНДЕКСАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
