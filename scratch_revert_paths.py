import os

html_path = r'd:\VINA\static\scanner.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('src="static/', 'src="')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

js_path = r'd:\VINA\static\scanner.js'
with open(js_path, 'r', encoding='utf-8') as f:
    js = f.read()

js = js.replace("'static/", "'")

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(js)

print('Reverted paths to relative')
