import os, re

# ==============================================================================
# 1. UPDATE STATIC/SCANNER.CSS
# ==============================================================================
with open('static/scanner.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Replace ochre on .btn-store-route
css = re.sub(
    r'\.btn-store-route\s*\{[^}]*\}',
    '''.btn-store-route {
    background: #722F37;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 9px 16px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    flex-shrink: 0;
    box-shadow: 0 2px 8px rgba(114, 47, 55, 0.25);
    transition: background 0.15s ease, transform 0.1s ease;
}
.btn-store-route:hover {
    background: #873842;
    transform: translateY(-1px);
}
.btn-store-route:active {
    background: #58111A;
    transform: translateY(1px);
}''',
    css
)

# Replace green on .walk-hud-box
css = re.sub(
    r'\.walk-hud-box\s*\{[^}]*\}',
    '''.walk-hud-box {
    background: #fdf2f4;
    border: 1.5px solid #722F37;
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 14px;
    display: none;
}''',
    css
)

# Replace green on .store-card-row.active-route
css = re.sub(
    r'\.store-card-row\.active-route\s*\{[^}]*\}',
    '''.store-card-row.active-route {
    border-color: #722F37;
    background: #fff8f9;
}''',
    css
)

# Replace ochre on .cat-chip.gold-badge
css = re.sub(
    r'\.cat-chip\.gold-badge\s*\{[^}]*\}',
    '''.cat-chip.gold-badge {
    background: #fdf2f4;
    border-color: #f1c2cb;
    color: #722F37;
    font-weight: 600;
}''',
    css
)
css = re.sub(
    r'\.cat-chip\.gold-badge\.selected\s*\{[^}]*\}',
    '''.cat-chip.gold-badge.selected {
    background: #722F37;
    color: #ffffff;
    border-color: #722F37;
}''',
    css
)

# Replace ochre on .history-badge-gold
css = re.sub(
    r'\.history-badge-gold\s*\{[^}]*\}',
    '''.history-badge-gold {
    background: #fdf2f4;
    border: 1px solid #f1c2cb;
    color: #722F37;
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
    display: inline-block;
    margin-bottom: 8px;
}''',
    css
)

# Add custom map markers and catalog/cart styling if not present
new_css_additions = '''
/* ==========================================================================
   КАСТОМНЫЕ МАРКЕРЫ НА КАРТЕ: ПОЛНЫЕ БОКАЛЫ ИЗ ОЦЕНКИ И ЗНАК ПОЛЬЗОВАТЕЛЯ
   ========================================================================== */
.vina-map-glass-marker {
    background: transparent !important;
    border: none !important;
    cursor: pointer;
}
.vina-map-marker-inner {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    position: relative;
    filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.35));
    transition: transform 0.15s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.vina-map-marker-inner:hover,
.vina-map-glass-marker.active-route .vina-map-marker-inner {
    transform: scale(1.15) translateY(-4px);
}
.vina-marker-glass-wrap {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}
.vina-marker-glass-icon {
    height: 44px;
    width: auto;
    object-fit: contain;
    display: block;
    filter: drop-shadow(0 3px 6px rgba(0,0,0,0.4));
}
.vina-marker-badge-num {
    position: absolute;
    top: -4px;
    right: -6px;
    background: #722F37;
    color: #ffffff;
    font-size: 11px;
    font-weight: 800;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: 2px solid #ffffff;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}
.vina-marker-label-name {
    margin-top: 3px;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #722F37;
    border-radius: 8px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 700;
    color: #1a1a1a;
    white-space: nowrap;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

.vina-map-user-marker {
    background: transparent !important;
    border: none !important;
}
.vina-user-marker-inner {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #ffffff;
    border: 2px solid #722F37;
    border-radius: 20px;
    padding: 3px 8px 3px 4px;
    box-shadow: 0 4px 12px rgba(114, 47, 55, 0.3);
    white-space: nowrap;
}
.vina-user-znak-img {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    object-fit: contain;
    flex-shrink: 0;
}
.vina-user-text {
    font-size: 11px;
    font-weight: 700;
    color: #722F37;
}

/* Кнопка «В корзину» на карточке вина */
.home-wine-card-bottom-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: auto;
    padding-top: 8px;
}
.btn-card-add-cart {
    background: #722F37;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
    transition: background 0.15s ease, transform 0.1s ease;
    box-shadow: 0 2px 6px rgba(114, 47, 55, 0.2);
}
.btn-card-add-cart:hover {
    background: #873842;
    transform: translateY(-1px);
}
.btn-card-add-cart:active {
    background: #58111A;
    transform: translateY(0);
}
.btn-card-add-cart.added {
    background: #28a745;
}

/* Тулбар корзины (Выбрать все / Удалить выбранные) */
.cart-action-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding: 6px 4px;
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #eef0f3;
}
.cart-select-all-btn {
    background: none;
    border: none;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 600;
    color: #495057;
    cursor: pointer;
    padding: 4px 6px;
}
.btn-cart-delete-selected {
    background: none;
    border: none;
    color: #722F37;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 8px;
    border-radius: 8px;
    transition: background 0.15s ease;
}
.btn-cart-delete-selected:hover {
    background: #fdf2f4;
}

/* Кнопка удаления одной позиции на карточке в корзине */
.cart-item-delete-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #8e8e93;
    cursor: pointer;
    transition: all 0.15s ease;
    padding: 0;
    z-index: 5;
}
.cart-item-delete-btn:hover {
    background: #722F37;
    color: #ffffff;
    border-color: #722F37;
}

/* Принудительно 2 в ряд в каталоге на всех экранах */
.catalog-grid {
    display: grid !important;
    grid-template-columns: repeat(2, 1fr) !important;
    gap: 12px !important;
    margin-bottom: 24px;
}
'''

if 'vina-map-glass-marker' not in css:
    css += '\n' + new_css_additions

with open('static/scanner.css', 'w', encoding='utf-8') as f:
    f.write(css)
print('Updated static/scanner.css')
