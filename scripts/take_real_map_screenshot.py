import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'
ud = tempfile.mkdtemp(prefix='edge_shot_map_')
shot_path = os.path.join(out_dir, 'preview_real_osm_wine_stores_map.png')

cmd = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--force-device-scale-factor=1',
    f'--user-data-dir={ud}', '--window-size=480,950', '--virtual-time-budget=5000',
    f'--screenshot={shot_path}', 'http://127.0.0.1:8080/scanner.html?preview_step=map'
]

res = subprocess.run(cmd, capture_output=True, text=True)
print('Screenshot result:', shot_path, 'exists:', os.path.exists(shot_path), 'code:', res.returncode)
