with open('static/scanner.html', 'r', encoding='utf-8') as f:
    content = f.read()

target = """                <!-- 8. Статический сектор выше нижней навигации: слева "Сомелье", справа "Добавить в корзину" (не двигается с лентой) -->
                <div class="detail-sticky-bar" id="detail-sticky-action-bar">
                    <button type="button" class="btn-sticky-somm" id="btn-detail-sticky-somm" onclick="openSommelierForDetailWine()">
                        <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" style="filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%);" alt="">
                        <span>Сомелье</span>
                    </button>
                    <button type="button" class="btn-sticky-cart" id="btn-detail-sticky-cart" onclick="addCurrentDetailWineToCart()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M5 7h14l-1 13H6L5 7z"></path>
                            <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                        </svg>
                        <span id="detail-sticky-cart-label">Добавить в корзину</span>
                    </button>
                </div>"""

replacement = """                <!-- 8. Статический сектор выше нижней навигации: слева "Сомелье", справа "Найти в магазинах" (не двигается с лентой) -->
                <div class="detail-sticky-bar" id="detail-sticky-action-bar">
                    <button type="button" class="btn-sticky-somm" id="btn-detail-sticky-somm" onclick="openSommelierForDetailWine()">
                        <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" style="filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%);" alt="">
                        <span>Спросить сомелье</span>
                    </button>
                    <button type="button" class="btn-sticky-map" id="btn-detail-sticky-map" onclick="findStoresForCurrentWine()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                            <circle cx="12" cy="10" r="3"></circle>
                        </svg>
                        <span>Найти в магазинах</span>
                    </button>
                </div>"""

assert target in content, "target not found"
content = content.replace(target, replacement, 1)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced detail-sticky-bar successfully!")
