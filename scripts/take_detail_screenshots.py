import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'

shots = [
    ('preview_wine_detail_top.png', 'file:///D:/VINA/static/scanner.html?preview_step=wine_detail'),
]

for fname, url in shots:
    ud = tempfile.mkdtemp(prefix='edge_detail_')
    out_path = os.path.join(out_dir, fname)
    cmd = [
        edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--force-device-scale-factor=1',
        f'--user-data-dir={ud}', '--window-size=480,932', '--virtual-time-budget=3000',
        f'--screenshot={out_path}', url
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print(fname, os.path.exists(out_path), res.returncode)
