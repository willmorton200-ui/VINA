# -*- coding: utf-8 -*-
import re

with open('d:/VINA/static/scanner.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace any complex addWineToCartDirectly call with addWineToCartDirectly('${w.slug}')
# For line 2061:
pattern1 = r"""<button type="button" class="btn-card-add-cart" onclick="event\.stopPropagation\(\);\s*addWineToCartDirectly\('\$\{w\.slug\}'[^>]+title="Добавить в корзину">"""
replacement = """<button type="button" class="btn-card-add-cart" onclick="event.stopPropagation(); addWineToCartDirectly('${w.slug}')" title="Добавить в корзину">"""

text = re.sub(pattern1, replacement, text)

with open('d:/VINA/static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Replaced all complex button calls with addWineToCartDirectly('${w.slug}')")
