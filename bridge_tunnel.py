"""
VINA - Cloudflare Tunnel Bridge Wrapper
Запускает cloudflared, фильтрует нефатальные внутренние логи (DNS resolver timeout),
извлекает рабочий HTTPS-адрес, копирует его в буфер обмена и выводит чистый статус.
"""
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

BIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "cloudflared.exe")

if not os.path.exists(BIN_PATH):
    print(f"[ОШИБКА] Не найден файл: {BIN_PATH}")
    sys.exit(1)

# Завершаем старые зависшие процессы cloudflared
subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"], capture_output=True)

cmd = [
    BIN_PATH,
    "tunnel",
    "--edge-ip-version", "4",
    "--protocol", "http2",
    "--url", "http://127.0.0.1:8080"
]

print("======================================================================")
print("          VINA: Cloudflare Tunnel Bridge к RTX 3090                   ")
print("======================================================================")
print("[1/2] Проверка локального сервера VINA (http://127.0.0.1:8080)...")

try:
    with urllib.request.urlopen("http://127.0.0.1:8080/api/health", timeout=2) as r:
        if r.status == 200:
            print("      [OK] Сервер VINA работает и отвечает!")
except Exception:
    print("      [ВНИМАНИЕ] Сервер на http://127.0.0.1:8080 пока не отвечает.")
    print("      Не забудьте запустить 'start_app.bat'!")

print("\n[2/2] Подключение к Cloudflare Edge (получение HTTPS адреса)...")

proc = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace",
    bufsize=1
)

tunnel_url = None
url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

try:
    for line in proc.stdout:
        line_clean = line.strip()
        if not line_clean:
            continue
        
        # Поиск URL туннеля
        if not tunnel_url:
            match = url_regex.search(line_clean)
            if match:
                tunnel_url = match.group(0)
                try:
                    with open("tunnel_url.txt", "w", encoding="utf-8") as f_u:
                        f_u.write(tunnel_url.strip())
                except Exception:
                    pass

                try:
                    subprocess.run("clip", input=tunnel_url.strip(), text=True, check=True)
                    copied_msg = "  [СКОПИРОВАНО В БУФЕР ОБМЕНА!]"
                except Exception:
                    copied_msg = ""
                
                print("\n" + "=" * 70)
                print("  >>> ПУБЛИЧНЫЙ HTTPS ТУННЕЛЬ СОЗДАН! <<<")
                print(f"  URL: {tunnel_url}{copied_msg}")
                print("=" * 70)
                print("  Ожидание регистрации соединения в сети Cloudflare...")
                continue

        if "Registered tunnel connection" in line_clean:
            print("\n" + "=" * 70)
            print("  >>> [ГОТОВО К РАБОТЕ] Соединение успешно установлено! <<<")
            print(f"  Вставьте этот адрес в мобильный сканер: {tunnel_url}")
            print("  Для остановки туннеля нажмите Ctrl+C.")
            print("=" * 70 + "\n")

            def _live_stats():
                last_reqs = 0
                while True:
                    time.sleep(3)
                    try:
                        with urllib.request.urlopen("http://127.0.0.1:20241/metrics", timeout=1) as m_resp:
                            m_text = m_resp.read().decode("utf-8")
                            for m_line in m_text.splitlines():
                                if m_line.startswith("cloudflared_tunnel_total_requests "):
                                    req_num = int(m_line.split()[-1])
                                    if req_num > last_reqs:
                                        print(f"  [+] Запрос со сканера передан в VINA (всего запросов: {req_num})")
                                        last_reqs = req_num
                    except Exception:
                        pass
            threading.Thread(target=_live_stats, daemon=True).start()
            continue

        # Фильтруем пугающий нефатальный шум DNS local resolver (и при старте, и при фоновом refresh)
        if "DNS local resolver" in line_clean or "v2.argotunnel.com: i/o timeout" in line_clean:
            continue
            
        # Фильтруем длинную сетку precheck
        if line_clean.startswith("|") or "precheck" in line_clean:
            continue

        if "ERR" in line_clean:
            print(f"[Cloudflare Log]: {line_clean}")
            
except KeyboardInterrupt:
    print("\nОстановка туннеля...")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
    print("Туннель остановлен.")
