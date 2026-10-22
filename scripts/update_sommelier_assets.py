import re

# 1. Update static/scanner.js
with open('static/scanner.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# Replace emoji in pairing chips
js_content = js_content.replace('🍽 ${escapeSommHtml(d.label)}', '${escapeSommHtml(d.label)}')
js_content = js_content.replace('🍽 ${escapeSommHtml(label)}', '${escapeSommHtml(label)}')

# Replace emoji in quick chips
js_content = js_content.replace('🍽 С чем подать?', 'С чем подать?')
js_content = js_content.replace('🍷 Профиль вкуса', 'Профиль вкуса')
js_content = js_content.replace('🔄 Найти аналоги', 'Найти аналоги')
js_content = js_content.replace('🥩 Стейк без дуба', 'Стейк без дуба')

# Replace emoji in pairing custom
js_content = js_content.replace('🍽 Блюдо:', 'Блюдо:')

# Replace emoji in toasts
js_content = js_content.replace("t.toast_title || '🥂 Авторский тост'", "t.toast_title || 'Авторский тост'")
js_content = js_content.replace('💡 Совет сомелье по подаче', 'Совет сомелье по подаче')
js_content = js_content.replace('🍷 Близнецы по вкусовому профилю в каталоге:', 'Близнецы по вкусовому профилю в каталоге:')

# Replace glass image in reset, typing indicator, assistant responses, logic box, history
js_content = js_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="">\n                    Логика употребления',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" alt="" style="width: 16px; height: 16px; object-fit: contain;">\n                    Логика употребления'
)
js_content = js_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="">\r\n                    Логика употребления',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" alt="" style="width: 16px; height: 16px; object-fit: contain;">\r\n                    Логика употребления'
)

# Assistant avatars in sommelier chat
js_content = js_content.replace(
    '<img src="img/glass_filled_straight.png" style="width: 16px; height: 22px; object-fit: contain;" alt="">',
    '<img src="svg/public-rating.svg" style="width: 18px; height: 18px; object-fit: contain;" alt="">'
)
js_content = js_content.replace(
    '<img src="img/glass_filled_straight.png" style="width: 16px; height: 22px; object-fit: contain;">',
    '<img src="svg/public-rating.svg" style="width: 18px; height: 18px; object-fit: contain;">'
)

# Wine history pill in detail
js_content = js_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> История вина',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 14px; height: 14px; object-fit: contain;" alt=""> История вина'
)

with open('static/scanner.js', 'w', encoding='utf-8') as f:
    f.write(js_content)
print('scanner.js updated successfully!')


# 2. Update static/scanner.html
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# Missing wine modal icon
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="missing-wine-icon-img" alt="">',
    '<img src="svg/public-rating.svg" class="missing-wine-icon-img" alt="" style="width: 32px; height: 32px; object-fit: contain;">'
)

# Missing wine modal button icon
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" style="filter: brightness(0) invert(1);" alt="">',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 18px; height: 18px; object-fit: contain; filter: brightness(0) invert(1);" alt="">'
)

# Admin dashboard header icon
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="">\n                        Дашборд сервиса VINA',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 18px; height: 18px; object-fit: contain;" alt="">\n                        Дашборд сервиса VINA'
)
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="">\r\n                        Дашборд сервиса VINA',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 18px; height: 18px; object-fit: contain;" alt="">\r\n                        Дашборд сервиса VINA'
)

# Toast badge in sommelier tab
html_content = html_content.replace(
    '<span class="cat-chip gold-badge" style="display: inline-block; margin-bottom: 8px;">🥂 Авторский тост сомелье</span>',
    '<span class="cat-chip gold-badge" style="display: inline-flex; align-items: center; gap: 6px; margin-bottom: 8px;"><img src="svg/public-rating.svg" style="width: 14px; height: 14px; object-fit: contain;" alt=""> Авторский тост сомелье</span>'
)

# Alternatives header in sommelier tab
html_content = html_content.replace(
    '<h4 style="margin: 16px 0 10px 0; font-size: 15px; color: #1a1a1a;">🔄 Похожие вина из каталога (если захотите альтернативу):</h4>',
    '<h4 style="margin: 16px 0 10px 0; font-size: 15px; color: #1a1a1a;">Похожие вина из каталога (если захотите альтернативу):</h4>'
)

# Wine history modal badge
html_content = html_content.replace(
    '<span class="history-badge-gold"><img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> Историческое досье',
    '<span class="history-badge-gold"><img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 14px; height: 14px; object-fit: contain;" alt=""> Историческое досье'
)

# Wine history pill in detail page
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> История вина',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 14px; height: 14px; object-fit: contain;" alt=""> История вина'
)

# Wine detail pairing chips emoji
html_content = html_content.replace(
    '🍽 ${bd.label} <span style="font-size: 10px; color: #28a745;',
    '${bd.label} <span style="font-size: 10px; color: #28a745;'
)

# Wine detail pairing verdict header emoji
html_content = html_content.replace(
    '<strong style="color: #722F37;">🍽 ${label}: ${verdictTitle}</strong>',
    '<strong style="color: #722F37;">${label}: ${verdictTitle}</strong>'
)

# Wine set modal icon
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" style="width: 16px; height: 18px; object-fit: contain;" alt="">\n                        </div>\n                        <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1a1a1a;">Собрать винный сет</h3>',
    '<img src="svg/public-rating.svg" style="width: 18px; height: 18px; object-fit: contain;" alt="">\n                        </div>\n                        <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1a1a1a;">Собрать винный сет</h3>'
)
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" style="width: 16px; height: 18px; object-fit: contain;" alt="">\r\n                        </div>\r\n                        <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1a1a1a;">Собрать винный сет</h3>',
    '<img src="svg/public-rating.svg" style="width: 18px; height: 18px; object-fit: contain;" alt="">\r\n                        </div>\r\n                        <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1a1a1a;">Собрать винный сет</h3>'
)

# Catalog empty state icon
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" style="width: 26px; height: 34px; object-fit: contain;" alt="">',
    '<img src="svg/public-rating.svg" style="width: 26px; height: 26px; object-fit: contain;" alt="">'
)

# Catalog card rating badge
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="" style="width: 14px; height: 16px; object-fit: contain;">\n                                    <span class="home-rating-score">',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" alt="" style="width: 14px; height: 14px; object-fit: contain;">\n                                    <span class="home-rating-score">'
)
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="" style="width: 14px; height: 16px; object-fit: contain;">\r\n                                    <span class="home-rating-score">',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" alt="" style="width: 14px; height: 14px; object-fit: contain;">\r\n                                    <span class="home-rating-score">'
)

# Filter checkboxes icons (Народный рейтинг, Высокий рейтинг, Вина с историей)
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> Народный рейтинг',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 14px; height: 14px; object-fit: contain;" alt=""> Народный рейтинг'
)
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> Высокий рейтинг',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 14px; height: 14px; object-fit: contain;" alt=""> Высокий рейтинг'
)
html_content = html_content.replace(
    '<img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> Вина с историей',
    '<img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 14px; height: 14px; object-fit: contain;" alt=""> Вина с историей'
)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
print('scanner.html updated successfully!')

with open('static/scanner.html', 'r', encoding='utf-8') as f:
    c = f.read().replace('🍷 СПИСОК ВИН К ПОКУПКЕ', 'СПИСОК ВИН К ПОКУПКЕ')
with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(c)

with open('static/scanner.js', 'r', encoding='utf-8') as f:
    c = f.read().replace("showToast('📍 Переход в раздел «Карта»')", "showToast('Переход в раздел «Карта»')")
with open('static/scanner.js', 'w', encoding='utf-8') as f:
    f.write(c)

print('Cleaned final emojis!')
