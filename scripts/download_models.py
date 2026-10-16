"""
Скрипт автоматической загрузки всех необходимых моделей для VINA Scanner.
Используется коллегами при развертывании в Docker или на чистой рабочей станции.

Скачивает:
1. Qwen2-VL-2B-Instruct (Vision Language Model для чтения сложных этикеток)
2. Проверяет наличие SigLIP 2, DINOv2-LoRA и YOLO моделей в папке models/

Запуск:
    python scripts/download_models.py
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"

def download_qwen2_vl():
    target_dir = MODELS_DIR / "Qwen2-VL-2B-Instruct"
    print(f"\n[1/2] Проверка модели Qwen2-VL-2B-Instruct в {target_dir}...")
    
    if target_dir.exists() and (any(target_dir.glob("*.safetensors")) or any(target_dir.glob("*.bin"))):
        print(f" -> Qwen2-VL-2B-Instruct уже установлена локально ({sum(f.stat().st_size for f in target_dir.glob('*')) / (1024**3):.2f} GB). Пропуск.")
        return True

    target_dir.mkdir(parents=True, exist_ok=True)
    repo_id = "Qwen/Qwen2-VL-2B-Instruct"
    token = os.environ.get("HF_TOKEN", None)
    
    print(f" -> Модель не найдена. Начинаем загрузку с Hugging Face ({repo_id})...")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
            token=token,
        )
        print(f" -> Успешно скачано в {target_dir}")
        return True
    except Exception as e_direct:
        print(f" -> Прямая загрузка не удалась ({e_direct}). Пробуем через зеркало hf-mirror.com...")
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(target_dir),
                local_dir_use_symlinks=False,
                token=token,
                endpoint="https://hf-mirror.com",
            )
            print(f" -> Успешно скачано через зеркало в {target_dir}")
            return True
        except Exception as e_mirror:
            print(f" [!] Ошибка скачивания Qwen2-VL: {e_mirror}")
            return False

def download_dinov2_small():
    target_dir = MODELS_DIR / "dinov2-small"
    print(f"\n[2/3] Проверка модели dinov2-small в {target_dir}...")
    if target_dir.exists() and (any(target_dir.glob("*.bin")) or any(target_dir.glob("*.safetensors"))):
        print(f" -> dinov2-small уже установлена локально. Пропуск.")
        return True

    target_dir.mkdir(parents=True, exist_ok=True)
    repo_id = "facebook/dinov2-small"
    print(f" -> Модель не найдена. Начинаем загрузку с Hugging Face ({repo_id})...")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
        )
        print(f" -> Успешно скачано в {target_dir}")
        return True
    except Exception as e_direct:
        print(f" -> Прямая загрузка не удалась ({e_direct}). Пробуем через зеркало hf-mirror.com...")
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=repo_id,
                local_dir=str(target_dir),
                local_dir_use_symlinks=False,
                endpoint="https://hf-mirror.com",
            )
            print(f" -> Успешно скачано через зеркало в {target_dir}")
            return True
        except Exception as e_mirror:
            print(f" [!] Ошибка скачивания dinov2-small: {e_mirror}")
            return False

def check_local_models():
    print(f"\n[3/3] Проверка встроенных моделей и индексов в {MODELS_DIR}...")
    required = [
        ("best_v2_100bottles.pt", "YOLOv8x-seg детекция бутылок и этикеток"),
        ("dinov2-small", "DINOv2 backbone"),
        ("dinov2_lora_all_wines", "DINOv2 LoRA адаптер вина"),
        ("dino_all_wines_index.faiss", "FAISS индекс DINOv2"),
        ("siglip2_index.faiss", "FAISS индекс SigLIP 2"),
    ]
    all_ok = True
    for item, desc in required:
        p = MODELS_DIR / item
        if p.exists():
            print(f" -> [OK] {item} ({desc})")
        else:
            print(f" -> [MISSING] {item} ({desc})")
            all_ok = False
    return all_ok

if __name__ == "__main__":
    print("=" * 70)
    print("VINA SCANNER: Автоматическая подготовка моделей")
    print("=" * 70)
    ok_qwen = download_qwen2_vl()
    ok_dino = download_dinov2_small()
    ok_local = check_local_models()
    print("=" * 70)
    if ok_qwen and ok_dino and ok_local:
        print("[ГОТОВО] Все модели на месте и готовы к работе.")
    else:
        print("[ВНИМАНИЕ] Некоторые модели отсутствуют, проверьте лог выше.")
