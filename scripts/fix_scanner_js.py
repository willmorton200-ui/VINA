with open('d:/VINA/static/scanner.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the first occurrence of const checkedCount in renderCartPanel
old = "const checkedCount = cart.filter(w => w.checked !== false).length;"
new = "const checkedSelectedCount = cart.filter(w => w.checked !== false).length;"
text = text.replace(old, new, 1)

old_span = "<span>Удалить выбранные (${checkedCount})</span>"
new_span = "<span>Удалить выбранные (${checkedSelectedCount})</span>"
text = text.replace(old_span, new_span, 1)

with open('d:/VINA/static/scanner.js', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patch applied")
