import subprocess, tempfile

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
ud = tempfile.mkdtemp(prefix='edge_dump_')

cmd = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    f'--user-data-dir={ud}', '--virtual-time-budget=3000', '--dump-dom',
    'file:///D:/VINA/static/scanner.html?preview_step=wine_detail'
]
res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
html = res.stdout

for id_name in ['header-center-brand', 'header-center-detail', 'detail-glasses-strip', 'detail-sticky-action-bar', 'detail-badge-score']:
    pos = html.find(f'id="{id_name}"')
    if pos != -1:
        print(f'=== {id_name} ===')
        print(html[pos-30:pos+250])
    else:
        print(f'=== {id_name} NOT FOUND ===')
