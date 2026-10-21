import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'

ud1 = tempfile.mkdtemp(prefix='edge_shot_home_plates_')
p1 = os.path.join(out_dir, 'preview_home_top_v4.png')
cmd1 = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--force-device-scale-factor=1',
    f'--user-data-dir={ud1}', '--window-size=480,932', '--virtual-time-budget=3000',
    f'--screenshot={p1}', 'file:///D:/VINA/static/scanner.html?preview_step=home'
]
res1 = subprocess.run(cmd1, capture_output=True, text=True)
print('p1 (home plates):', p1, os.path.exists(p1), res1.returncode)
