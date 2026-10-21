with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

target1 = """В наличии: <b>${s.bottles_left} бут.</b> · Цена: <b>${s.price_rub} ₽</b>"""
replacement1 = """В наличии: <b>${s.bottles_left} бут.</b>"""

target2 = """В наличии: ${s.bottles_left} бут. (${s.price_rub} ₽)"""
replacement2 = """В наличии: ${s.bottles_left} бут."""

assert target1 in html, "target1 not found"
assert target2 in html, "target2 not found"

html = html.replace(target1, replacement1, 1)
html = html.replace(target2, replacement2, 1)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Removed prices from map store cards!")
