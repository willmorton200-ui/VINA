import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'

shots = [
    ('preview_wine_detail_card.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_detail'),
    ('preview_wine_detail_lightbox.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_detail_zoom'),
    ('preview_wine_detail_zoomed_label.png', 'http://127.0.0.1:8080/static/scanner.html?preview_step=wine_detail_zoomed_2x'),
]

for filename, url in shots:
    ud = tempfile.mkdtemp(prefix='edge_shot_zoom_')
    out_path = os.path.join(out_dir, filename)
    cmd = [
        edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--force-device-scale-factor=1',
        f'--user-data-dir={ud}', '--window-size=480,932', '--virtual-time-budget=3000',
        f'--screenshot={out_path}', url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(filename, '->', os.path.exists(out_path), 'code:', res.returncode)
