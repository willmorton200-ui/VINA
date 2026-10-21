import re

with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update Header to add #header-center-detail
target_header = """            <div class="logo header-center-logo" onclick="switchHubTab('home')" style="cursor: pointer;">
                <img src="znak.png" alt="Свое вино" class="header-brand-znak">
                <span>Свое вино</span>
            </div>"""

new_header = """            <div class="logo header-center-logo" id="header-center-brand" onclick="switchHubTab('home')" style="cursor: pointer;">
                <img src="znak.png" alt="Свое вино" class="header-brand-znak">
                <span>Свое вино</span>
            </div>

            <!-- Заголовок карточки товара: Артикул + Поделиться ссылкой -->
            <div class="header-center-detail" id="header-center-detail" style="display: none; align-items: center; gap: 8px;">
                <span class="detail-header-article" id="detail-header-article">Арт. 482910</span>
                <button type="button" class="header-share-btn" id="btn-header-share" onclick="shareCurrentWine()" title="Поделиться ссылкой">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="18" cy="5" r="3"></circle>
                        <circle cx="6" cy="12" r="3"></circle>
                        <circle cx="18" cy="19" r="3"></circle>
                        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                    </svg>
                </button>
            </div>"""

if target_header in html:
    html = html.replace(target_header, new_header)
    print("1. Header updated successfully")
else:
    print("1. Target header not found")

# 2. Update Cart icon with badge
target_cart = """            <button type="button" class="bnav-item" id="bnav-cart" onclick="switchHubTab('cart')">
                <div class="bnav-icon-wrap">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M5 7h14l-1 13H6L5 7z"></path>
                        <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                        <path d="M9.5 11v2a2.5 2.5 0 0 0 5 0v-2"></path>
                    </svg>
                </div>
                <span class="bnav-label">Корзина</span>
            </button>"""

new_cart = """            <button type="button" class="bnav-item" id="bnav-cart" onclick="switchHubTab('cart')">
                <div class="bnav-icon-wrap">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M5 7h14l-1 13H6L5 7z"></path>
                        <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                        <path d="M9.5 11v2a2.5 2.5 0 0 0 5 0v-2"></path>
                    </svg>
                    <span id="bnav-cart-badge" class="bnav-badge hidden">0</span>
                </div>
                <span class="bnav-label">Корзина</span>
            </button>"""

if target_cart in html:
    html = html.replace(target_cart, new_cart)
    print("2. Cart badge added successfully")
else:
    print("2. Target cart not found")

# 3. Update catalog-detail-view HTML
detail_view_start = '<div id="catalog-detail-view"'
detail_view_end = '<!-- /catalog-detail-view -->'

new_detail_view = """<div id="catalog-detail-view" style="display: none; padding-bottom: 96px;">
                <!-- Верхняя панель возврата в каталог -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                    <button class="btn-back" onclick="closeWineDetail()" style="margin-bottom: 0; background: #ffffff; border: 1px solid #dee2e6; border-radius: 12px; padding: 8px 16px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; font-weight: 600; color: #1a1a1a;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M15 18l-6-6 6-6" />
                        </svg>
                        Назад в каталог
                    </button>
                    <div id="detail-history-pill-top"></div>
                </div>

                <div class="hub-card" style="padding: 18px;">
                    <!-- 1. Квадратный экранчик: бутылка помещается полностью + сердечко в избранное справа вверху -->
                    <div class="detail-wine-square-frame" id="detail-wine-square-frame">
                        <button type="button" class="detail-wine-fav-btn" id="detail-wine-fav-btn" onclick="toggleCurrentDetailFavorite()" title="Добавить в Избранное">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#8e8e93" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                            </svg>
                        </button>
                        <img id="detail-wine-img" src="" alt="Бутылка вина" class="detail-wine-bottle-full">
                    </div>

                    <!-- 2. Производитель, Название вина, Теги -->
                    <div class="detail-wine-meta" style="margin-bottom: 12px;">
                        <div id="detail-wine-winery" style="font-size: 13px; font-weight: 600; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px;"></div>
                        <h2 id="detail-wine-title" style="margin: 4px 0 10px 0; font-size: 22px; color: #1a1a1a; line-height: 1.3;"></h2>

                        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px;">
                            <span id="detail-wine-alcohol" class="cat-tag-pill" style="background: #fdf2f4; color: var(--primary); font-weight: 700; border-color: #f8d7da;">13.5% об.</span>
                            <span id="detail-wine-color" class="cat-tag-pill" style="font-weight: 600;">Красное</span>
                            <span id="detail-wine-sugar" class="cat-tag-pill" style="font-weight: 600;">Сухое</span>
                            <span id="detail-wine-region" class="cat-tag-pill" style="font-weight: 600;">Крым</span>
                            <span id="detail-wine-grape" class="cat-tag-pill" style="background: #f8f9fa;">Сорт: Каберне</span>
                        </div>

                        <!-- 3. Оценка народного рейтинга: цифра до 5 + рюмочки цветные/серые + количество оценок ПОД сортом -->
                        <div class="detail-rating-strip-row" id="detail-rating-strip-row" style="display: flex; align-items: center; gap: 10px; margin: 12px 0 16px 0; padding: 4px 0;">
                            <span class="detail-rating-strip-score" id="detail-badge-score" style="font-size: 20px; font-weight: 700; color: #1a1a1a;">4,5</span>
                            <div class="detail-rating-strip-glasses" id="detail-glasses-strip" style="display: flex; align-items: center; gap: 5px;"></div>
                            <span class="detail-rating-strip-votes" style="font-size: 13px; color: #495057; font-weight: 500;">(<span id="detail-badge-votes">16</span> оценок)</span>
                        </div>
                    </div>

                    <!-- 4. Органолептический профиль и баланс вкуса (полоски тоньше в 1,5 раза, строго бордовый и серый) -->
                    <div style="margin-bottom: 22px;">
                        <h4 style="margin: 0 0 10px 0; font-size: 14px; font-weight: 700; color: #1a1a1a; display: flex; align-items: center; gap: 6px;">
                            <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" style="filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%);" alt="">
                            Органолептический профиль и баланс вкуса
                        </h4>
                        <div id="detail-sensory-bars"></div>
                    </div>

                    <!-- 5. Описание вина -->
                    <div style="margin-bottom: 22px;">
                        <h4 style="margin: 0 0 6px 0; font-size: 14px; font-weight: 700; color: #1a1a1a;">Описание</h4>
                        <p id="detail-wine-description" style="margin: 0; font-size: 14px; line-height: 1.6; color: #495057;"></p>
                    </div>

                    <!-- 6. История вина (только при наличии) -->
                    <div id="detail-wine-history-block" style="display: none; margin-bottom: 22px; background: #fffcf4; border: 1px solid #fae8b6; border-radius: 12px; padding: 14px;">
                        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 6px;">
                            <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="">
                            <strong style="color: #856404; font-size: 14px;">История вина:</strong>
                            <span id="detail-wine-history-year" style="font-size: 12px; font-weight: 700; color: #856404;"></span>
                        </div>
                        <p id="detail-wine-history-headline" style="margin: 0 0 8px 0; font-weight: 600; font-size: 13px; color: #533f03;"></p>
                        <p id="detail-wine-history-text" style="margin: 0; font-size: 13px; line-height: 1.5; color: #664d03;"></p>
                        <div id="detail-wine-history-events" style="margin-top: 10px;"></div>
                    </div>

                    <!-- 7. Интерактивная оценка (Поставь свою оценку) -->
                    <section class="rating-section" id="detail-rating-section" style="margin-bottom: 10px; border: 1px solid #f1f3f5;">
                        <h3>Поставь свою оценку</h3>
                        <div class="glasses-container" id="detail-glasses-container">
                            <div class="glass-slot" data-index="1"><img src="img/glass_empty_straight.png" alt="1" class="glass-img"></div>
                            <div class="glass-slot" data-index="2"><img src="img/glass_empty_straight.png" alt="2" class="glass-img"></div>
                            <div class="glass-slot" data-index="3"><img src="img/glass_empty_straight.png" alt="3" class="glass-img"></div>
                            <div class="glass-slot" data-index="4"><img src="img/glass_empty_straight.png" alt="4" class="glass-img"></div>
                            <div class="glass-slot" data-index="5"><img src="img/glass_empty_straight.png" alt="5" class="glass-img"></div>
                        </div>
                        <div class="rating-stats">
                            <div id="detail-user-rating-text">Ваша оценка: - из 5</div>
                            <div class="stats-small">Всего оценок: <span id="detail-total-votes">15</span> &bull; Средний балл: <span id="detail-avg-score">4.5</span></div>
                        </div>
                    </section>
                </div>

                <!-- 8. Статический сектор выше нижней навигации: слева "Сомелье", справа "Добавить в корзину" (не двигается с лентой) -->
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
                </div>
            </div>"""

start_pos = html.find(detail_view_start)
end_pos = html.find(detail_view_end)

if start_pos != -1 and end_pos != -1:
    html = html[:start_pos] + new_detail_view + "\n            " + html[end_pos:]
    print("3. Detail view markup updated successfully")
else:
    print("3. Detail view bounds not found:", start_pos, end_pos)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)
