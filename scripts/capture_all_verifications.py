import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'

shots = [
    ('preview_catalog_2col.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=catalog', 4000),
    ('preview_map_burgundy_glasses.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=map', 4500),
    ('preview_cart_delete_toolbar.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=cart_with_items', 3000),
    ('preview_profile_wines_tape.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=profile', 3000),
    ('preview_profile_bought_tape.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=profile_bought', 3000),
]

for filename, url, budget in shots:
    ud = tempfile.mkdtemp(prefix='edge_shot_all_')
    out_path = os.path.join(out_dir, filename)
    cmd = [
        edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--force-device-scale-factor=1',
        f'--user-data-dir={ud}', '--window-size=440,920', f'--virtual-time-budget={budget}',
        f'--screenshot={out_path}', url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    print(f"{filename} -> {os.path.exists(out_path)} ({size} bytes, exit {res.returncode})")
