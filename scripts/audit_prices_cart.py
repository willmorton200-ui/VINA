import re

with open('static/scanner.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("--- PRICE MATCHES IN scanner.html ---")
for i, line in enumerate(lines):
    if re.search(r'(\d+[\s\xa0]*₽|class="[^"]*price[^"]*"|id="[^"]*price[^"]*"|цена|ценник)', line, re.IGNORECASE):
        print(f"L{i+1}: {line.strip()[:140]}")

print("\n--- CART MATCHES IN scanner.html ---")
for i, line in enumerate(lines):
    if re.search(r'(bnav-cart|hub-panel-cart|btn-card-add-cart|btn-sticky-cart|addWineToCart|addCurrentDetailWineToCart|корзин)', line, re.IGNORECASE):
        print(f"L{i+1}: {line.strip()[:140]}")
