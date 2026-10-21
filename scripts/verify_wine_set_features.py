import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'

tests = [
    ('preview_wine_detail_card_unified.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_detail', 4000),
    ('preview_wine_detail_from_scanner.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_detail_scanner', 4000),
    ('preview_wine_set_modal_selector.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_set_modal', 4000),
    ('preview_wine_set_modal_generated.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_set_generated', 4500),
    ('preview_favorites_with_sets.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=favorites_with_sets', 4000),
]

for filename, url, budget in tests:
    ud = tempfile.mkdtemp(prefix='edge_shot_wineset_')
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
