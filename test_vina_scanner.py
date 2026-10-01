
#!/usr/bin/env python3
"""
Тест точности и времени отклика для проекта VINA Scanner.
Совместим с форматом организатора и заказчика (owner_eval: пакеты 1 и 2).

Режимы работы:
  1) direct (по умолчанию) — прямой сверхбыстрый тест через SigLIP2 + FAISS WineSearchEngine (~20-25 мс/кадр).
  2) http — проверка через HTTP API сервер VINA Studio (http://127.0.0.1:8080/v1/eval/predict).
  3) cascade — каскадный тест: SigLIP + VINA STUDIO OCR + текстовый матчинг (требует GPU).
"""

import argparse
import hashlib
import json
import mimetypes
import os
import sys
import time
from pathlib import Path
import cv2
import httpx


def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_http_eval(queries, images_dir: Path, endpoint: str, output_path: Path, mapping: dict):
    print(f"\n[HTTP РЕЖИМ] Отправка запросов на {endpoint}...")
    client = httpx.Client(timeout=60.0)

    base_url = endpoint.rsplit("/", 2)[0]
    try:
        r = client.get(f"{base_url}/api/health", timeout=2.0)
        if r.status_code == 200:
            print("✓ Сервер VINA Studio активен и готов к обработке.")
    except Exception as e:
        print(f"Предупреждение: Сервер на {endpoint} не отвечает ({e}). Убедитесь, что запущен app.py!")

    correct = 0
    total = len(queries)
    latencies = []

    print("\n" + "-" * 80)
    print(f"{'#':<3} | {'Query ID':<9} | {'Файл':<14} | {'Статус':<7} | {'Top-1 Slug':<32} | {'Conf':<8} | {'Время'}")
    print("-" * 80)

    with open(output_path, "w", encoding="utf-8", newline="\n") as out_f:
        for idx, (query_id, image_relpath) in enumerate(queries, 1):
            image_file = images_dir / image_relpath
            if not image_file.is_file():
                continue

            img_sha256 = calculate_sha256(image_file)
            mime_type, _ = mimetypes.guess_type(str(image_file))
            if not mime_type:
                mime_type = "image/jpeg"

            t0 = time.perf_counter()
            predicted_slug = None
            latency_ms = 0
            err_msg = ""
            confidence = 0.0
            decision_source = ""

            try:
                with open(image_file, "rb") as f:
                    files = {"image": (image_file.name, f, mime_type)}
                    resp = client.post(endpoint, files=files)
                latency_ms = round((time.perf_counter() - t0) * 1000)

                if resp.status_code == 200:
                    data = resp.json()
                    predicted_slug = data.get("slug")
                    confidence = data.get("confidence_percent", data.get("confidence", 0.0) * 100)
                    decision_source = data.get("decision_source", "unknown")
                else:
                    err_msg = f"HTTP {resp.status_code}"
            except Exception as e:
                latency_ms = round((time.perf_counter() - t0) * 1000)
                err_msg = str(e)[:25]

            latencies.append(latency_ms)
            expected = mapping.get(query_id)
            ok = (predicted_slug and predicted_slug == expected)
            if ok:
                correct += 1
                status = "✓ OK"
            else:
                status = "✗ FAIL"

            slug_disp = (predicted_slug or err_msg or "null")[:32]
            conf_disp = f"{confidence:.1f}%"
            print(f"{idx:02d} | {query_id:<9} | {image_relpath:<14} | {status:<7} | {slug_disp:<32} | {conf_disp:<8} | {latency_ms} ms ({decision_source})")
            if not ok and expected:
                print(f"    ↳ Ожидался : {expected}")
                print(f"    ↳ Получен  : {predicted_slug}")

            record = {
                "query_id": query_id,
                "image_path": image_relpath,
                "image_sha256": img_sha256,
                "predicted_slug": predicted_slug,
                "confidence": round(confidence, 2),
                "decision_source": decision_source,
                "latency_ms": latency_ms,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    return correct, total, latencies


def run_direct_eval(queries, images_dir: Path, output_path: Path, mapping: dict):
    print("\n[DIRECT РЕЖИМ] Инициализация движка VINA WineSearchEngine (SigLIP2 + FAISS)...")
    sys.path.insert(0, str(Path(__file__).parent))
    from pipeline.catalog import WineCatalog
    from pipeline.search_engine import WineSearchEngine

    csv_file = r"D:\VINA\TZ\Датасет\Датасет\strapi_output0709.csv"
    uploads = r"D:\VINA\TZ\Датасет\Датасет\prod-svoe-vino-strapi\prod-svoe-vino\strapi\uploads"

    catalog = WineCatalog(csv_file, uploads)
    engine = WineSearchEngine(catalog, use_gpu=True)

    correct = 0
    total = len(queries)
    latencies = []

    print("\n" + "-" * 80)
    print(f"{'#':<3} | {'Query ID':<9} | {'Файл':<14} | {'Статус':<7} | {'Top-1 Slug':<32} | {'Время'}")
    print("-" * 80)

    with open(output_path, "w", encoding="utf-8", newline="\n") as out_f:
        for idx, (query_id, image_relpath) in enumerate(queries, 1):
            image_file = images_dir / image_relpath
            if not image_file.is_file():
                continue

            img_sha256 = calculate_sha256(image_file)
            img_bgr = cv2.imread(str(image_file))

            t0 = time.perf_counter()
            results = engine.search_by_cv2_image(img_bgr, top_k=1)
            latency_ms = round((time.perf_counter() - t0) * 1000)
            latencies.append(latency_ms)

            predicted_slug = results[0]["slug"] if results else None
            expected = mapping.get(query_id)
            ok = (predicted_slug and predicted_slug == expected)
            if ok:
                correct += 1
                status = "✓ OK"
            else:
                status = "✗ FAIL"

            slug_disp = (predicted_slug or "null")[:32]
            print(f"{idx:02d} | {query_id:<9} | {image_relpath:<14} | {status:<7} | {slug_disp:<32} | {latency_ms} ms")
            if not ok and expected:
                print(f"    ↳ Ожидался : {expected}")
                print(f"    ↳ Получен  : {predicted_slug}")

            record = {
                "query_id": query_id,
                "image_path": image_relpath,
                "image_sha256": img_sha256,
                "predicted_slug": predicted_slug,
                "latency_ms": latency_ms,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

    return correct, total, latencies


def main():
    parser = argparse.ArgumentParser(description="Тест точности и производительности VINA Scanner")
    parser.add_argument("--run", type=str, default="1", choices=["1", "2"], help="Номер прогона заказчика (1: каталожные, 2: полевые)")
    parser.add_argument("--mode", type=str, default="direct", choices=["direct", "http"], help="Режим: direct (локальный движок) или http (веб-сервер)")
    parser.add_argument("--endpoint", type=str, default="http://127.0.0.1:8080/v1/eval/predict", help="HTTP эндпоинт для режима http")
    parser.add_argument("--eval-root", type=Path, default=Path(r"D:\VINA2\owner_eval"), help="Путь к папке owner_eval")
    args = parser.parse_args()

    pack_dir = args.eval_root / args.run
    manifest_path = pack_dir / "queries.tsv"
    mapping_path = pack_dir / "mapping.json"
    images_dir = pack_dir / "queries"

    output_dir = Path(r"D:\VINA\eval_results") / args.run
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "predictions_vina.jsonl"

    print("=" * 80)
    print(f"      ТЕСТ СИСТЕМЫ РАСПОЗНАВАНИЯ VINA SCANNER (ПРОГОН {args.run})")
    print("=" * 80)
    print(f"• Режим тестирования: {args.mode.upper()}")
    print(f"• Пакет данных      : {pack_dir}")
    print(f"• Папка с фото      : {images_dir}")
    print(f"• Манифест          : {manifest_path}")
    print(f"• Результат         : {output_path}")
    print("=" * 80)

    if not manifest_path.is_file() or not images_dir.is_dir():
        print(f"ОШИБКА: Тестовые файлы не найдены в {pack_dir}", file=sys.stderr)
        return 1

    mapping = {}
    if mapping_path.is_file():
        m_data = json.loads(mapping_path.read_text(encoding="utf-8"))
        mapping = {c["query_id"]: c.get("expected_slug") for c in m_data.get("cases", [])}

    queries = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines()[1:]:
        line = line.strip()
        if line:
            parts = line.split("\t")
            if len(parts) >= 2:
                queries.append((parts[0].strip(), parts[1].strip()))

    t_start = time.perf_counter()
    if args.mode == "http":
        correct, total, latencies = run_http_eval(queries, images_dir, args.endpoint, output_path, mapping)
    else:
        correct, total, latencies = run_direct_eval(queries, images_dir, output_path, mapping)

    total_time = time.perf_counter() - t_start
    pct = (correct / total * 100.0) if total > 0 else 0.0
    avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

    print("\n" + "=" * 80)
    print(f" ИТОГОВЫЕ РЕЗУЛЬТАТЫ VINA SCANNER (ПРОГОН {args.run}):")
    print("=" * 80)
    print(f"• Режим           : {args.mode.upper()}")
    print(f"• Файл ответов    : {output_path}")
    print(f"• Всего запросов  : {total}")
    print(f"• Точность Hit@1  : {correct}/{total} ({pct:.1f}%)")
    print(f"• Время отклика   : среднее {avg_lat:.0f} ms (мин: {min(latencies)} ms, макс: {max(latencies)} ms)")
    print(f"• Общее время     : {total_time:.1f} с")
    print("=" * 80 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
