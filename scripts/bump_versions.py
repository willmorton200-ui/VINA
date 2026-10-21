with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('scanner.css?v=40_cart', 'scanner.css?v=41_nocart', 1)
html = html.replace('scanner.js?v=35_cart', 'scanner.js?v=36_nocart', 1)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Bumped version strings in scanner.html successfully!")
