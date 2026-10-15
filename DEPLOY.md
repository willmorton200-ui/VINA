# Руководство по развертыванию VINA Scanner (Deployment Guide)

Данное руководство содержит пошаговые инструкции по развертыванию сервиса компьютерного зрения **VINA** на сервере или рабочей станции.

---

## Вариант 1: Быстрое развертывание в Docker на Ubuntu 22.04 / 24.04 (Рекомендуется)

Этот способ гарантирует полную изоляцию, отсутствие конфликтов версий библиотек и автоматический запуск при перезагрузке сервера.

### Шаг 1. Подготовка сервера с GPU NVIDIA

1. Убедитесь, что установлены драйверы NVIDIA:

   ```bash
   nvidia-smi
   ```

   *(Команда должна показывать модель видеокарты и версию драйвера).*

2. Установите Docker (если не установлен):

   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. Установите **NVIDIA Container Toolkit** (для доступа Docker к GPU):

   ```bash
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
     && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
       sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
       sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list \
     && sudo apt-get update \
     && sudo apt-get install -y nvidia-container-toolkit

   # Перезапустите Docker демон
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

4. Проверьте доступность GPU в Docker:

   ```bash
   docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
   ```

---

### Шаг 2. Клонирование репозитория

```bash
git clone https://github.com/willmorton200-ui/VINA.git
cd VINA
```

---

### Шаг 3. Запуск контейнера

Запустите контейнер в фоновом режиме через Docker Compose:

```bash
docker compose up -d --build
```

Docker соберет образ, установит системные зависимости OpenCV/FAISS и запустит сервис на порту **8080**.

---

### Шаг 4. Проверка работоспособности

1. Проверьте статус контейнера и healthcheck:

   ```bash
   docker compose ps
   ```

   *(Статус должен стать `Up ... (healthy)`).*

2. Выполните запрос к эндпоинту состояния:

   ```bash
   curl http://localhost:8080/api/health
   ```

   Пример успешного ответа:

   ```json
   {
     "status": "healthy",
     "gpu_available": true,
     "gpu_name": "NVIDIA GeForce RTX 3090",
     "catalog_size": 2103,
     "faiss_index_size": 4111,
     "dino_available": true,
     "dino_index_size": 2069,
     "ranker_mode": "Hybrid v2 (SigLIP2 + DINOv2-LoRA + OCR Formula)"
   }
   ```

3. Тестовый запрос на инференс этикетки:

   ```bash
   curl -X POST -F "image=@/path/to/bottle.jpg" http://localhost:8080/v1/eval/predict
   ```

---

### Полезные команды управления контейнером

* **Просмотр логов в реальном времени:**

  ```bash
  docker compose logs -f vina-scanner
  ```

* **Перезапуск сервиса:**

  ```bash
  docker compose restart
  ```

* **Остановка контейнера:**

  ```bash
  docker compose down
  ```

---

## Вариант 2: Установка без Docker (Bare-Metal Linux / systemd)

Используйте этот вариант, если на сервере нет Docker или требуется запуск напрямую через systemd-сервис.

### 1. Установка системных библиотек

```bash
sudo apt-get update && sudo apt-get install -y \
    python3-pip \
    python3-venv \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    git
```

### 2. Клонирование и создание venv

```bash
git clone https://github.com/willmorton200-ui/VINA.git
cd VINA

python3 -m venv venv
source venv/bin/activate
```

### 3. Установка PyTorch и библиотек

```bash
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### 4. Создание systemd-сервиса (Автозапуск)

Создайте файл `/etc/systemd/system/vina.service`:

```ini
[Unit]
Description=VINA Wine Scanner API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/ubuntu/VINA
Environment="PATH=/home/ubuntu/VINA/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/ubuntu/VINA/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8080 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Активируйте и запустите службу:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vina
sudo systemctl start vina
sudo systemctl status vina
```

---

## Вариант 3: Запуск на рабочей станции Windows

Для разработчиков и локального тестирования под Windows:

1. Убедитесь, что установлены:
   * Python 3.10 или 3.11 ([python.org](https://www.python.org/downloads/))
   * Git for Windows ([git-scm.com](https://git-scm.com/))
   * NVIDIA Driver с поддержкой CUDA 12.1+

2. Откройте PowerShell в папке проекта:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   pip install -r requirements.txt
   ```

3. Запуск:
   Дважды кликните по файлу **`start_app.bat`** или выполните в консоли:

   ```powershell
   python app.py
   ```

   Сервер запустится на `http://127.0.0.1:8080` и автоматически откроет сканер в браузере.

---

## Часто задаваемые вопросы (Траблшутинг)

### 1. `CUDA out of memory`

* Пайплайн оптимизирован для работы в ~4-6 ГБ VRAM (SigLIP2 + DINOv2-LoRA + YOLOv8x).
* Если видеокарта имеет менее 8 ГБ VRAM, отключите параллельную загрузку фолбэка Qwen2-VL или перенаправьте VLM на CPU.

### 2. Порт 8080 уже занят

* В файле `docker-compose.yml` измените проброс портов, например `"8081:8080"`.
* Либо при запуске uvicorn укажите флаг `--port 8081`.

### 3. Сервер запустился, но возвращает ошибку `Image not found`

* База вин (`wines_integrated_clean.csv`) содержит полную текстовую семантику 2103 вин. Если физические фото вин из интернет-магазина не были смонтированы в `wines_images_clean/`, поиск все равно работает штатно по векторным эмбеддингам и OCR. Картинки оригиналов из каталога подтягиваются автоматически при их наличии.
