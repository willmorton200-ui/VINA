import time
import os
import cv2
import json
from fastapi.testclient import TestClient

print("=" * 60)
print("  VINA: Комплексное тестирование серверных эндпоинтов")
print("=" * 60)

from app import app, catalog, search_engine

client = TestClient(app)

# 1. Тест health
print("\n[TEST 1] Проверка состояния сервера (/api/health)...")
res_health = client.get("/api/health")
print(f"Status: {res_health.status_code}, Response: {res_health.json()}")
assert res_health.status_code == 200

# 2. Тест UI эндпоинтов
print("\n[TEST 2] Проверка HTML страниц (/ и /scanner)...")
res_root = client.get("/")
assert res_root.status_code == 200
print(f"GET / -> {res_root.status_code} OK (Размер: {len(res_root.text)} байт)")

res_scanner = client.get("/scanner")
assert res_scanner.status_code == 200
print(f"GET /scanner -> {res_scanner.status_code} OK (Размер: {len(res_scanner.text)} байт)")

# 3. Тест официального бенчмарка РСХБ.Цифра (/v1/eval/predict)
print("\n[TEST 3] Официальный бенчмарк РСХБ (/v1/eval/predict) на queries.tsv:")
queries_dir = r"D:\VINA\TZ\Датасет\Датасет\eval\queries"
manifest_path = r"D:\VINA\TZ\Датасет\Датасет\eval\queries.tsv"

with open(manifest_path, "r", encoding="utf-8") as f:
    lines = [line.strip().split("\t") for line in f if line.strip()][1:]

total_latencies = []

for q_id, img_name in lines:
    img_path = os.path.join(queries_dir, img_name)
    if not os.path.exists(img_path):
        print(f"  Внимание: {img_path} не найден")
        continue

    with open(img_path, "rb") as img_f:
        t0 = time.time()
        res = client.post("/v1/eval/predict", files={"image": (img_name, img_f, "image/jpeg")})
        dt_ms = (time.time() - t0) * 1000
        total_latencies.append(dt_ms)

    assert res.status_code == 200, f"Error {res.status_code}: {res.text}"
    data = res.json()
    slug = data.get("slug")

    wine_info = catalog.get_wine(slug) if slug else None
    wine_name = wine_info.get("name") if wine_info else "Не найдено в каталоге"

    sla_status = "✅ SLA PASS (<3c)" if dt_ms < 3000 else "❌ SLA FAIL (>3c)"
    print(f"  Запрос: {q_id} ({img_name})")
    print(f"    - Предсказанный slug: '{slug}'")
    print(f"    - Вино: {wine_name}")
    print(f"    - Время ответа: {dt_ms:.1f} ms [{sla_status}]")

avg_latency = sum(total_latencies) / len(total_latencies) if total_latencies else 0
print(f"\n  📊 Среднее время инференса (SLA): {avg_latency:.1f} ms")

# 4. Тест получения карточки вина и фото
if slug:
    print(f"\n[TEST 4] Получение карточки вина (/api/wine/{slug})...")
    res_wine = client.get(f"/api/wine/{slug}")
    assert res_wine.status_code == 200
    print(f"Status: {res_wine.status_code}, Винодельня: {res_wine.json().get('winery')}, Регион: {res_wine.json().get('region')}")

    print(f"\n[TEST 5] Загрузка оригинального изображения (/api/image/{slug})...")
    res_img = client.get(f"/api/image/{slug}")
    print(f"Status: {res_img.status_code}, Content-Type: {res_img.headers.get('content-type')}, Размер: {len(res_img.content)} байт")
    assert res_img.status_code == 200

# 5. Тест CV пайплайна деварпинга и OCR
print("\n[TEST 6] Тест Cylindrical Dewarping & OCR (/api/process_upload)...")
test_bottle = r"D:\VINA\test_dataset\butilki\castillo_liria_pair.jpg"
if os.path.exists(test_bottle):
    with open(test_bottle, "rb") as f:
        t0 = time.time()
        res_cv = client.post("/api/process_upload", files={"file": ("bottle.jpg", f, "image/jpeg")})
        dt_cv = time.time() - t0
    
    assert res_cv.status_code == 200, f"Error {res_cv.status_code}: {res_cv.text}"
    cv_data = res_cv.json()
    print(f"Status: {res_cv.status_code} OK (Время: {dt_cv:.2f}с)")
    text = cv_data.get('recognized_text', '')
    print(f"  - Текст OCR: '{text[:60]}...'")
    print(f"  - Отрезок резкости: {cv_data.get('dewarped_sharpness')}")
else:
    print(f"  Пропуск: {test_bottle} не найден")

print("\n" + "=" * 60)
print("  ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
print("=" * 60)
