import os

src_html = r'd:\VINA\static\scanner.html'
with open(src_html, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Change scanner.css to style.css
html = html.replace('scanner.css?v=3', 'style.css')
html = html.replace('scanner.css', 'style.css')

# 2. Add canvas overlay to scanner-frame
overlay_tag = '<canvas id="overlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 5; pointer-events: none;"></canvas>'
html = html.replace('<video id="camera-feed"', '<video id="camera-feed"')
html = html.replace('</video>', f'</video>\n                {overlay_tag}')

# 3. Fix script tags
old_scripts = '<script src="scanner.js"></script>'
new_scripts = '''<script src="config.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/onnxruntime-web@1.18.0/dist/ort.min.js" crossorigin="anonymous"></script>
    <script type="module" src="app.js"></script>'''
html = html.replace(old_scripts, new_scripts)

# 4. Remove /static/ from asset paths since they are directly in /mobi/ (which maps to web/)
html = html.replace('src="static/', 'src="')
html = html.replace('src="/static/', 'src="')

dest_html = r'D:\VINA2\lct2026prod\web\index.html'
with open(dest_html, 'w', encoding='utf-8') as f:
    f.write(html)
print('Wrote index.html')
