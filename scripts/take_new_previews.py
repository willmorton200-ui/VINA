import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'

# 1. Home screen with promo bar and clean search input
ud1 = tempfile.mkdtemp(prefix='edge_shot_home_')
p1 = os.path.join(out_dir, 'preview_home_top_v3.png')
cmd1 = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--force-device-scale-factor=1',
    f'--user-data-dir={ud1}', '--window-size=480,932', '--virtual-time-budget=3000',
    f'--screenshot={p1}', 'file:///D:/VINA/static/scanner.html?preview_step=home'
]
res1 = subprocess.run(cmd1, capture_output=True, text=True)
print('p1 (home):', p1, os.path.exists(p1), res1.returncode)

# 2. Scanner screen with znak snap button and full-width Choose Photo button
ud2 = tempfile.mkdtemp(prefix='edge_shot_scanner_')
p2 = os.path.join(out_dir, 'preview_scanner_view_v2.png')
cmd2 = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--force-device-scale-factor=1',
    f'--user-data-dir={ud2}', '--window-size=480,932', '--virtual-time-budget=3000',
    f'--screenshot={p2}', 'file:///D:/VINA/static/scanner.html?preview_step=scanner'
]
res2 = subprocess.run(cmd2, capture_output=True, text=True)
print('p2 (scanner):', p2, os.path.exists(p2), res2.returncode)

# 3. Direct load (demonstration splash sequence constantly appearing)
ud3 = tempfile.mkdtemp(prefix='edge_shot_demo_splash_')
p3 = os.path.join(out_dir, 'preview_demo_splash_always.png')
cmd3 = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--force-device-scale-factor=1',
    f'--user-data-dir={ud3}', '--window-size=480,932', '--virtual-time-budget=3000',
    f'--screenshot={p3}', 'file:///D:/VINA/static/scanner.html'
]
res3 = subprocess.run(cmd3, capture_output=True, text=True)
print('p3 (demo splash):', p3, os.path.exists(p3), res3.returncode)
