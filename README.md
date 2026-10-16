<!-- markdownlint-disable MD033 -->
# VINA: Сервис компьютерного зрения и распознавания винных этикеток

<p align="center">
  <img src="static/znak.png" alt="VINA Logo" width="160">
</p>

<p align="center">
  <b>Высокоточная система распознавания вин по фотографии бутылки для интернет-магазина «Своё Вино» (РСХБ.Цифра)</b><br>
  <i>YOLOv8-seg • Cylindrical Dewarping • SigLIP 2 • DINOv2-LoRA • Qwen2-VL • Multi-Vector FAISS</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Accuracy_Test_1-100%25_(27%2F27)-brightgreen" alt="Test 1 Accuracy">
  <img src="https://img.shields.io/badge/Accuracy_Test_2-100%25_(25%2F25)-brightgreen" alt="Test 2 Accuracy">
  <img src="https://img.shields.io/badge/Accuracy_Eval_100-95.0%25_(95%2F100)-success" alt="Eval 100 Accuracy">
  <img src="https://img.shields.io/badge/Response_Time-~2.1s_(SLA<3s)-blue" alt="Latency">
  <img src="https://img.shields.io/badge/PyTorch-2.2+-ee4c2c" alt="PyTorch">
  <img src="https://img.shields.io/badge/CUDA-12.1+-76b900" alt="CUDA">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ed" alt="Docker">
</p>

---

## 🏆 Результаты бенчмарков

Система прошла калибровку и валидацию на всех контрольных наборах данных:

| Тестовый набор | Описание | Точность (Hit@1) | Среднее время | Статус |
| :--- | :--- | :---: | :---: | :---: |
| **Тест 1 (`owner_eval/1`)** | Каталожные и студийные фото (27 бутылок) | **100.0% (27 / 27)** | ~2 044 мс | ✅ Идеально |
| **Тест 2 (`owner_eval/2`)** | Полевые сложные фото, блики, углы (25 бутылок) | **100.0% (25 / 25)** | ~2 111 мс | ✅ Идеально |
| **Финальный Eval (`D:\Eval`)** | Полный пакет конкурса (100 бутылок) | **95.0% (95 / 100)** | ~2 314 мс | ✅ Топ-результат |

> **Примечание по Eval 100:** В пакете из 100 бутылок 90 из 95 каталожных вин определяются безошибочно (94.7%), а 5 вин независимого гаражного винодела Литавщука, отсутствующие в базе магазина «Своё Вино», корректно отсекаются по порогу уверенности (`< 86.0%`) со статусом `not_in_catalog` (возвращается `slug: null`).

---

## 🧠 Ключевые архитектурные решения

1. **Иерархическая сегментация бутылки и этикетки (Stage 1)**
   * Дообученная модель `YOLOv8x-seg` (`models/best_v2_100bottles.pt`).
   * Функция выбора центральной бутылки с квадратичным штрафом за удаление от оптической оси кадра $W_{\text{centrality}} = (1 - \Delta x)^2$.
   * Сохранение и вертикальная сшивка основной этикетки и соосных дополнительных шильдиков/кольереток.

2. **Цилиндрический деварпинг (Cylindrical Dewarping Stages 2–4)**
   * Векторизация физического контура этикетки, детектирование 4 углов и боковых образующих цилиндра.
   * Трансфинитная интерполяция кривизны (Coon's Patch) и ресемплинг через Thin Plate Spline (TPS) с фильтром Lanczos-4.

3. **Двухвекторный мультимодальный поиск (SigLIP 2 + DINOv2-LoRA)**
   * **SigLIP 2** (`ViT-B-16-SigLIP2-384`): извлекает глобальные семантические признаки всей композиции бутылки.
   * **DINOv2-small + LoRA** (`dinov2_lora_all_wines`): тонкоструктурные текстурные признаки кропа этикетки, обученные различать одинаковые линейки одного производителя.

4. **Гибридный калиброванный ранкинг (HybridRanker v2)**
   * Построение пула кандидатов Top-3 SigLIP + Top-3 DINO + расширение кластером «сестринских вин» линейки.
   * Формула доверия:
     $$IF = N + IB \cdot (A + C + D + F)$$
     * $N$ — калиброванная визуальная уверенность эмбеддингов (0..100%).
     * $IB$ — масштабный коэффициент значимости OCR-бонуса.
     * $A$ (Артикул / Название), $C$ (Сорт винограда / Тезаурус), $D$ (Цвет / Сахар), $F$ (Тонкие маркеры линейки).
   * Поддержка цветовых микро-патчей (выделение шильдиков купажей, например, «Фантом 30/70», «50/50», «70/30»).

5. **Оркестратор VINA Studio Matcher и Sommelier**
   * Векторный индекс FAISS (2 103 эталона каталога, 4 111 ракурсов).
   * Интерактивный винный сомелье на базе локальной LLM/NLP с рекомендациями по гастрономии и винным вкусам.

---

## 📂 Структура проекта

```text
VINA/
├── app.py                      # FastAPI сервер (REST API, WebSocket, Swagger)
├── bridge_tunnel.py            # Облачный мост Cloudflare Tunnel с автокопированием URL
├── start_app.bat               # Быстрый запуск сервера на локальном GPU (RTX 3090)
├── start_tunnel.bat            # Запуск безопасного публичного HTTPS-туннеля
├── запустить_тест_1.bat        # Прогон 1 (27 каталожных фото)
├── запустить_тест_2.bat        # Прогон 2 (25 сложных полевых фото)
├── запустить_тест_eval.bat     # Финальный прогон Eval (100 бутылок конкурса)
├── test_vina_scanner.py        # Официальный кроссплатформенный раннер тестов
├── pipeline/                   # Модули алгоритмов компьютерного зрения
│   ├── dewarp_engine.py        # Полный конвейер цилиндрической развертки
│   ├── dino_engine.py          # DINOv2-LoRA экстрактор признаков
│   ├── hybrid_ranker.py        # Калиброванное слияние и формула бонусов
│   ├── search_engine.py        # SigLIP 2 + FAISS поисковый движок
│   └── vina_studio_matcher.py  # Студийный каскадный матчер
├── sommelier/                  # Модуль рекомендательного ассистента сомелье
├── static/                     # Веб-интерфейс мобильного сканера (PWA, HTML/CSS/JS)
├── models/                     # Обученные веса нейросетей и индексы FAISS
├── experiments/                # Исторические исследования, скрипты и отчеты
├── Dockerfile                  # Production Docker образ с CUDA 12.1
└── docker-compose.yml          # Оркестрация контейнеров
```

---

## 🚀 Развертывание и запуск

### Способ 1: Запуск в Docker (Рекомендуемый для продакшна)

Контейнер уже настроен для работы с видеокартами NVIDIA (через NVIDIA Container Toolkit) и содержит все системные библиотеки (OpenCV, FAISS OpenMP, cuDNN).

#### 1. Предварительные требования

* Установленный [Docker](https://docs.docker.com/engine/install/) и [Docker Compose](https://docs.docker.com/compose/).
* Для аппаратного ускорения: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html).

#### 2. Запуск контейнера

В корневой папке проекта выполните:

```bash
docker compose up -d --build
```

#### 3. Проверка статуса

```bash
docker compose ps
curl http://localhost:8080/api/health
```

Логи сервиса:

```bash
docker compose logs -f vina-scanner
```

Остановка:

```bash
docker compose down
```

---

### Способ 2: Локальная установка (Bare-metal: Windows / Linux)

#### 1. Требования к окружению

* **Python:** 3.10 или 3.11
* **GPU (желательно):** NVIDIA RTX 3060 / 3090 / 4090 / A100 (CUDA 12.1+)
* **CPU Fallback:** Поддерживается автоматический переход на CPU, если GPU отсутствует.

#### 2. Создание виртуального окружения

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 3. Установка PyTorch с поддержкой CUDA

Рекомендуется сначала установить PyTorch под вашу версию CUDA (например, CUDA 12.1):

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

#### 4. Установка зависимостей проекта

```bash
pip install -r requirements.txt
```

#### 5. Запуск сервера

**Под Windows:**

Дважды кликните по `start_app.bat` или выполните:

```bash
python app.py
```

Сервер запустится на `http://0.0.0.0:8080` и автоматически откроет сканер в браузере.

---

## 📡 API Спецификация

### 1. Официальный метод распознавания (SLA < 3 сек)

Используется жюри и тестовыми скриптами для оценки качества.

* **URL:** `POST /v1/eval/predict`
* **Content-Type:** `multipart/form-data`
* **Параметры:** `image` (файл изображения JPG/PNG/WebP)

**Пример запроса через curl:**

```bash
curl -X POST -F "image=@bottle_sample.jpg" http://127.0.0.1:8080/v1/eval/predict
```

**Пример ответа (вино найдено в каталоге):**

```json
{
  "slug": "golubitskoe-estate-rose-rozovoe-suhoe-125",
  "name": "Голубицкое Эстейт Розе",
  "score": 0.9239,
  "confidence": 0.9239,
  "confidence_percent": 92.39,
  "confidence_embedding": 88.89,
  "ocr_bonus": 3.5,
  "status": "found",
  "engine": "hybrid_v2 (SigLIP2 + DINOv2-LoRA + OCR Formula)",
  "total_time_ms": 2110.5
}
```

**Пример ответа (вино отсутствует в каталоге):**

```json
{
  "slug": null,
  "name": "",
  "score": 0.0,
  "confidence": 0.0,
  "confidence_percent": 0.0,
  "status": "not_in_catalog"
}
```

---

### 2. Проверка состояния системы (Healthcheck)

* **URL:** `GET /api/health`

**Пример ответа:**

```json
{
  "status": "healthy",
  "gpu_available": true,
  "gpu_name": "NVIDIA GeForce RTX 3090",
  "torch_version": "2.2.1+cu121",
  "catalog_size": 2103,
  "faiss_index_size": 4111,
  "dino_available": true,
  "dino_index_size": 2069,
  "ranker_mode": "Hybrid v2 (SigLIP2 + DINOv2-LoRA + OCR Formula)"
}
```

---

### 3. Мобильный сканер (PWA UI)

Откройте в браузере мобильного устройства или десктопа:

```text
http://<IP_СЕРВЕРА>:8080/scanner
```

Интерфейс поддерживает доступ к камере смартфона в реальном времени, мгновенный кроп этикетки, анимацию развертки и отображение карточки вина с характеристиками (сорт, сладость, цвет, регион, гастрономические пары).

---

## 🧪 Валидация и тестирование точности

Для запуска полного цикла тестирования используется скрипт `test_vina_scanner.py`.

### Тест 1 (Каталожные вина, 27 бутылок)

```bash
python test_vina_scanner.py --run 1 --mode http
```

*Результат: 27/27 (100.0%) OK.*

### Тест 2 (Полевые фото, 25 бутылок)

```bash
python test_vina_scanner.py --run 2 --mode http
```

*Результат: 25/25 (100.0%) OK.*

### Финальный пакет (100 бутылок)

```bash
python test_vina_scanner.py --run eval --mode http
```

*Результат: 95/100 (95.0%) OK (с сохранением файла ответов `predictions.jsonl`).*

---

## ⚙️ Переменные окружения

| Переменная | По умолчанию | Описание |
| :--- | :---: | :--- |
| `VINA_MATCHER_MODE` | `hybrid` | Режим работы матчера: `hybrid` (SigLIP2 + DINOv2-LoRA) или `legacy` |
| `PYTHONUNBUFFERED` | `1` | Мгновенный вывод логов Python в stdout/stderr |
| `CUDA_VISIBLE_DEVICES` | `0` | Индекс видеокарты для инференса |

---

## 👥 Авторы и лицензия

Проект разработан для конкурса **РСХБ.Цифра (Хакатон Своё Вино)**.  
Лицензия: [MIT](LICENSE).
