import os

def update_file(filepath, replacements):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (does not exist)")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content
    for old, new in replacements:
        content = content.replace(old, new)
    if content != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")
    else:
        print(f"No changes in {filepath}")

# 1. sommelier/stores_and_history.py
update_file('sommelier/stores_and_history.py', [
    ('Фирменная винотека «Своё Вино»', 'Фирменный магазин «Своё Вино»'),
    ('Винотека «Южный Сомелье & Энотека»', 'Магазин «Южный Сомелье & Энотека»'),
    ('Гастро-винотека «Крым и Кубань»', 'Гастро-магазин «Крым и Кубань»'),
    ('до ближайшей винотеки', 'до ближайшего магазина'),
])

# 2. static/scanner.js
update_file('static/scanner.js', [
    ('Самовывоз из винотеки', 'Самовывоз из магазина'),
    ('удобной винотеке', 'удобном магазине'),
])

# 3. static/scanner.html
update_file('static/scanner.html', [
    ('каталог вашего города и винотеки рядом', 'каталог вашего города и магазины рядом'),
    ('title="Карта винотек"', 'title="Карта магазинов"'),
    ('Самовывоз из винотеки', 'Самовывоз из магазина'),
    ('в удобной винотеке', 'в удобном магазине'),
    ('Винотека «Свое Вино» Центр', 'Магазин «Свое Вино» Центр'),
    ('Винотека «Кубань-Вино»', 'Магазин «Кубань-Вино»'),
])

print("Replacements finished successfully.")
