
#!/usr/bin/env python3
r"""
Кроссплатформенный (Windows / Linux) скрипт для запуска теста организатора/заказчика.
Пакеты: 1 (каталожные фото), 2 (полевые фото), 119 (119 полевых фото).
Автоопределение бэкенда: VINA Studio (8080) -> LCT2026 (8030).
"""

import argparse
import hashlib
import json
import mimetypes
import sys
import time
from pathlib import Path
import httpx

# Регистрация дополнительных mime-типов
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/png", ".png")


def calculate_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def detect_endpoint(requested_endpoint: str | None) -> str:
    if requested_endpoint:
        return requested_endpoint

    # VINA Studio (8080) приоритетнее LCT2026 (8030)
    candidates = [
        ("http://127.0.0.1:8080/api/health", "http://127.0.0.1:8080/v1/eval/predict", "VINA Studio (port 8080)"),
        ("http://127.0.0.1:8030/api/ready", "http://127.0.0.1:8030/api/v1/eval/predict", "LCT2026 Production (port 8030)"),
    ]

    with httpx.Client(timeout=1.0) as client:
        for check_url, predict_url, name in candidates:
            try:
                resp = client.get(check_url)
                if resp.status_code == 200:
                    print(f"[INFO] Обнаружен активный сервер: {name}")
                    return predict_url
            except Exception:
                pass

    # По умолчанию VINA Studio (порт 8080)
    return "http://127.0.0.1:8080/v1/eval/predict"


def run_evaluation(
    images_dir: Path,
    manifest_path: Path,
    mapping_path: Path,
    endpoint: str,
    output_path: Path,
    timeout: float = 60.0,
):
    print("=" * 80)
    print("      ТЕСТ ОТ ЗАКАЗЧИКА / ОРГАНИЗАТОРА (PARTICIPANT EVALUATION)")
    print("=" * 80)
    print(f"• Папка с фото      : {images_dir}")
    print(f"• Манифест          : {manifest_path}")
    print(f"• Endpoint сервиса  : {endpoint}")
    print(f"• Файл результатов  : {output_path}")
    if mapping_path and mapping_path.is_file():
        print(f"• Эталон разметки   : {mapping_path}")
    print("=" * 80)

    if not images_dir.is_dir():
        print(f"ОШИБКА: Папка с изображениями не найдена: {images_dir}", file=sys.stderr)
        return 1

    if not manifest_path.is_file():
        print(f"ОШИБКА: Манифест не найден: {manifest_path}", file=sys.stderr)
        return 1

    # Загружаем эталонный mapping (если есть)
    mapping = {}
    if mapping_path and mapping_path.is_file():
        try:
            m_data = json.loads(mapping_path.read_text(encoding="utf-8"))
            for c in m_data.get("cases", []):
                mapping[c["query_id"]] = c.get("expected_slug")
        except Exception as e:
            print(f"Предупреждение: Не удалось прочитать {mapping_path}: {e}")

    # Читаем манифест queries.tsv (header: query_id \t image_path)
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        print("ОШИБКА: Манифест пуст", file=sys.stderr)
        return 1

    header = lines[0].strip().split("\t")
    if len(header) < 2 or header[0] != "query_id" or header[1] != "image_path":
        print(f"ОШИБКА: Неверный заголовок манифеста: {lines[0]}", file=sys.stderr)
        return 1

    queries = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            queries.append((parts[0].strip(), parts[1].strip()))

    print(f"\nЗагружено запросов для проверки: {len(queries)}")

    total = len(queries)
    correct = 0
    latencies = []

    # Удаляем старый файл результатов если он был
    if output_path.exists():
        try:
            output_path.unlink()
        except Exception:
            pass

    client = httpx.Client(timeout=timeout)

    print(f"Проверка подключения к {endpoint}...")
    try:
        base_url = endpoint.rsplit("/", 2)[0]
        connected = False
        for hurl in [f"{base_url}/api/ready", f"{base_url}/api/health", f"{base_url}/api/ping"]:
            try:
                r = client.get(hurl, timeout=2.0)
                if r.status_code == 200:
                    connected = True
                    print(f"✓ Сервис активен и готов к инференсу ({hurl})")
                    break
            except Exception:
                pass
        if not connected:
            print("Предупреждение: Health-проверка не ответила 200, приступаем к отправке изображений...")
    except Exception as e:
        print(f"Предупреждение при проверке связи: {e}")

    print("\n" + "-" * 80)
    print(f"{'#':<3} | {'Query ID':<9} | {'Файл':<14} | {'Статус':<7} | {'Top-1 Slug':<32} | {'Время'}")
    print("-" * 80)

    with open(output_path, "w", encoding="utf-8", newline="\n") as out_f:
        for idx, (query_id, image_relpath) in enumerate(queries, 1):
            image_file = images_dir / image_relpath
            if not image_file.is_file():
                print(f"{idx:03d} | {query_id:<9} | {image_relpath:<14} | ✗ НЕТ   | Файл не найден в queries/  | 0 ms")
                record = {
                    "query_id": query_id,
                    "image_path": image_relpath,
                    "image_sha256": "",
                    "predicted_slug": None,
                    "latency_ms": 0,
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()
                continue

            img_sha256 = calculate_sha256(image_file)
            mime_type, _ = mimetypes.guess_type(str(image_file))
            if not mime_type:
                mime_type = "image/jpeg"

            t0 = time.perf_counter()
            predicted_slug = None
            latency_ms = 0
            err_msg = ""

            try:
                with open(image_file, "rb") as f:
                    files = {"image": (image_file.name, f, mime_type)}
                    resp = client.post(endpoint, files=files)
                latency_ms = round((time.perf_counter() - t0) * 1000)

                if resp.status_code in (200, 201):
                    try:
                        resp_data = resp.json()
                        if isinstance(resp_data, dict):
                            predicted_slug = resp_data.get("slug")
                        elif isinstance(resp_data, list) and len(resp_data) > 0 and isinstance(resp_data[0], dict):
                            predicted_slug = resp_data[0].get("slug")
                    except Exception:
                        predicted_slug = None
                else:
                    err_msg = f"HTTP {resp.status_code}"
            except Exception as exc:
                latency_ms = round((time.perf_counter() - t0) * 1000)
                err_msg = str(exc)[:30]

            if not predicted_slug:
                predicted_slug = None

            latencies.append(latency_ms)

            # Сверка с эталоном
            expected = mapping.get(query_id)
            if expected:
                if predicted_slug and predicted_slug == expected:
                    status = "✓ OK"
                    correct += 1
                else:
                    status = "✗ FAIL"
            else:
                status = "• PRED"

            slug_display = (predicted_slug or (err_msg if err_msg else "null"))[:32]
            print(f"{idx:03d} | {query_id:<9} | {image_relpath:<14} | {status:<7} | {slug_display:<32} | {latency_ms} ms")
            if status == "✗ FAIL":
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

    print("=" * 80)
    print(" ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print("=" * 80)
    print(f"• Файл с ответами сохранён: {output_path}")
    print(f"• Всего запросов  : {total}")
    if mapping:
        pct = (correct / total * 100.0) if total > 0 else 0.0
        print(f"• Точность Hit@1  : {correct}/{total} ({pct:.1f}%)")
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        print(f"• Время отклика   : среднее {avg_lat:.0f} ms (мин: {min(latencies)} ms, макс: {max(latencies)} ms)")
    print("=" * 80 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Запуск тестового прогона заказчика (owner_eval)")
    parser.add_argument("--run", type=str, default="1", choices=["1", "2", "119"], help="Номер тестового пакета: 1, 2 или 119")
    parser.add_argument("--images-dir", type=Path, default=None, help="Путь к папке с изображениями")
    parser.add_argument("--manifest", type=Path, default=None, help="Путь к queries.tsv")
    parser.add_argument("--mapping", type=Path, default=None, help="Путь к mapping.json")
    parser.add_argument("--output", type=Path, default=None, help="Путь для predictions.jsonl")
    parser.add_argument(
        "--endpoint",
        type=str,
        default=None,
        help="URL эндпоинта для предсказания (если не указан, определяется автоматически)",
    )
    parser.add_argument("--timeout", type=float, default=60.0, help="Таймаут запроса в секундах (по умолчанию 60)")

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent / args.run
    images_dir = args.images_dir or (base_dir / "queries")
    manifest = args.manifest or (base_dir / "queries.tsv")
    mapping = args.mapping or (base_dir / "mapping.json")
    output = args.output or (base_dir / "predictions.jsonl")

    endpoint = detect_endpoint(args.endpoint)

    return run_evaluation(
        images_dir=images_dir,
        manifest_path=manifest,
        mapping_path=mapping,
        endpoint=endpoint,
        output_path=output,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())
