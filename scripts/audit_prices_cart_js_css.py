import re

print("--- SCANNER.JS ---")
with open('static/scanner.js', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if re.search(r'(bnav-cart|hub-panel-cart|btn-card-add-cart|btn-sticky-cart|addWineToCart|addCurrentDetailWineToCart|корзин|home-wine-price)', line, re.IGNORECASE):
            print(f"L{i+1}: {line.strip()[:140]}")

print("\n--- SCANNER.CSS ---")
with open('static/scanner.css', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if re.search(r'(bnav-cart|hub-panel-cart|btn-card-add-cart|btn-sticky-cart|addWineToCart|addCurrentDetailWineToCart|корзин|home-wine-price)', line, re.IGNORECASE):
            print(f"L{i+1}: {line.strip()[:140]}")
