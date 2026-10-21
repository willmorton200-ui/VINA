with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update catalog-main-view to include class home-page-wrap
html = html.replace('<div id="catalog-main-view">', '<div id="catalog-main-view" class="home-page-wrap">', 1)

# 2. Replace the hub-card containing catalog search and chips with the exact home-style header
target = """                <!-- Основная область каталога -->
                <div class="catalog-main-area">
                    <div class="hub-card" style="padding: 16px 18px 14px 18px; margin-bottom: 14px;">
                        <!-- Строка поиска -->
                        <div class="catalog-search-wrap">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"></circle>
                                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                            </svg>
                            <input type="text" id="cat-search-q" class="catalog-search-input" placeholder="Поиск вина, сорта или производителя..." oninput="debounceCatalogSearch()">
                        </div>

                        <!-- Быстрые фильтры-чипсы (горизонтальный свайп на мобильном) -->
                        <div class="cat-chips-row">
                            <button class="cat-chip" id="btn-open-mobile-filter" onclick="toggleMobileSidebar()">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px; vertical-align: middle;">
                                    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
                                </svg>
                                Фильтры <span id="mobile-filter-badge" class="badge-count hidden">0</span>
                            </button>
                            <button class="cat-chip selected" data-color="" onclick="selectColorFilter(this, '')">Все</button>
                            <button class="cat-chip" data-color="Красное" onclick="selectColorFilter(this, 'Красное')">Красное</button>
                            <button class="cat-chip" data-color="Белое" onclick="selectColorFilter(this, 'Белое')">Белое</button>
                            <button class="cat-chip" data-color="Розовое" onclick="selectColorFilter(this, 'Розовое')">Розовое</button>
                            <button class="cat-chip gold-badge" id="btn-cat-hist-toggle" onclick="toggleCatalogHistoryFilter(this)">
                                <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> С историей
                            </button>
                            <button class="cat-chip" data-rating="4.8" onclick="quickFilterRating(this, '4.8')">
                                <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> 4.8+
                            </button>
                            <button class="cat-chip" data-sugar="Сухое" onclick="quickFilterSugar(this, 'Сухое')">Сухое</button>
                            <button class="cat-chip" data-sugar="Полусладкое" onclick="quickFilterSugar(this, 'Полусладкое')">Полусладкое</button>
                        </div>

                        <!-- Выпадающие списки фильтров (компактный мобильный вариант) -->
                        <div class="catalog-filters-grid">
                            <select id="cat-filter-sugar" class="cat-select" onchange="triggerCatalogReload()">
                                <option value="">Любая сухость</option>
                                <option value="Сухое">Сухое</option>
                                <option value="Полусухое">Полусухое</option>
                                <option value="Полусладкое">Полусладкое</option>
                                <option value="Сладкое">Сладкое / Крепленое</option>
                            </select>

                            <select id="cat-filter-region" class="cat-select" onchange="triggerCatalogReload()">
                                <option value="">Все регионы</option>
                                <option value="Кубань">Кубань</option>
                                <option value="Крым">Крым</option>
                                <option value="Долина Дона">Долина Дона</option>
                                <option value="Дагестан">Дагестан</option>
                                <option value="Нижняя Волга">Нижняя Волга</option>
                            </select>

                            <select id="cat-filter-grape" class="cat-select" onchange="triggerCatalogReload()">
                                <option value="">Все сорта</option>
                                <option value="Каберне">Каберне Совиньон / Фран</option>
                                <option value="Мерло">Мерло</option>
                                <option value="Саперави">Саперави</option>
                                <option value="Красностоп">Красностоп</option>
                                <option value="Шардоне">Шардоне</option>
                                <option value="Рислинг">Рислинг</option>
                                <option value="Совиньон">Совиньон Блан</option>
                                <option value="Мускат">Мускат</option>
                                <option value="Пино Нуар">Пино Нуар</option>
                            </select>

                            <select id="cat-filter-winery" class="cat-select" onchange="triggerCatalogReload()">
                                <option value="">Все винодельни</option>
                                <option value="Литавщук">Литавщук</option>
                                <option value="Фанагория">Фанагория</option>
                                <option value="Ведерниковъ">Ведерниковъ</option>
                                <option value="Массандра">Массандра</option>
                                <option value="Мысхако">Мысхако</option>
                                <option value="Абрау-Дюрсо">Абрау-Дюрсо</option>
                                <option value="Сикоры">Имение Сикоры</option>
                                <option value="Шато де Талю">Шато де Талю</option>
                                <option value="Гай-Кодзор">Гай-Кодзор</option>
                                <option value="Новый Свет">Новый Свет</option>
                            </select>

                            <select id="cat-filter-dish" class="cat-select" onchange="triggerCatalogReload()">
                                <option value="">Гастросочетания</option>
                                <option value="steak">BBQ, стейки и гриль</option>
                                <option value="fish">Рыба и морепродукты</option>
                                <option value="poultry">Блюда из птицы</option>
                                <option value="cheese">Сыры и брускетты</option>
                                <option value="dessert">Выпечка и десерты</option>
                            </select>

                            <select id="cat-filter-rating" class="cat-select" onchange="triggerCatalogReload()">
                                <option value="">Любой рейтинг</option>
                                <option value="4.8">от 4.8 (Топ вин)</option>
                                <option value="4.5">от 4.5 (Высокий)</option>
                            </select>
                        </div>
                    </div>"""

replacement = """                <!-- Основная область каталога -->
                <div class="catalog-main-area">
                    <!-- 1. Строка поиска вина точь-в-точь как на главной странице -->
                    <div class="home-search-bar" style="margin-bottom: 10px;">
                        <svg class="home-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8e8e93" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" onclick="debounceCatalogSearch()">
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        </svg>
                        <input
                            type="text"
                            id="cat-search-q"
                            class="home-search-input"
                            placeholder="Поиск вина в каталоге..."
                            oninput="debounceCatalogSearch()"
                            onkeydown="if(event.key==='Enter') debounceCatalogSearch()"
                        />
                    </div>

                    <!-- 2. Плашка Сканер вин (как на главной) -->
                    <div class="home-action-plate" onclick="openCameraFromHome()" title="Открыть сканер вин">
                        Сканер вин — Узнай Свое вино по фото!
                    </div>

                    <!-- 3. Плашка Сомелье (как на главной) -->
                    <div class="home-action-plate" onclick="openSommelierFromHome()" title="Открыть Сомелье" style="margin-bottom: 14px;">
                        Сомелье
                    </div>

                    <!-- 4. Быстрые фильтры-чипсы (горизонтальный свайп на мобильном) -->
                    <div class="cat-chips-row" style="margin-bottom: 14px;">
                        <button class="cat-chip" id="btn-open-mobile-filter" onclick="toggleMobileSidebar()">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px; vertical-align: middle;">
                                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
                            </svg>
                            Фильтры <span id="mobile-filter-badge" class="badge-count hidden">0</span>
                        </button>
                        <button class="cat-chip selected" data-color="" onclick="selectColorFilter(this, '')">Все</button>
                        <button class="cat-chip" data-color="Красное" onclick="selectColorFilter(this, 'Красное')">Красное</button>
                        <button class="cat-chip" data-color="Белое" onclick="selectColorFilter(this, 'Белое')">Белое</button>
                        <button class="cat-chip" data-color="Розовое" onclick="selectColorFilter(this, 'Розовое')">Розовое</button>
                        <button class="cat-chip gold-badge" id="btn-cat-hist-toggle" onclick="toggleCatalogHistoryFilter(this)">
                            <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> С историей
                        </button>
                        <button class="cat-chip" data-rating="4.8" onclick="quickFilterRating(this, '4.8')">
                            <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> 4.8+
                        </button>
                        <button class="cat-chip" data-sugar="Сухое" onclick="quickFilterSugar(this, 'Сухое')">Сухое</button>
                        <button class="cat-chip" data-sugar="Полусладкое" onclick="quickFilterSugar(this, 'Полусладкое')">Полусладкое</button>
                    </div>

                    <!-- Выпадающие списки фильтров (компактный десктопный вариант) -->
                    <div class="catalog-filters-grid" style="margin-bottom: 12px;">
                        <select id="cat-filter-sugar" class="cat-select" onchange="triggerCatalogReload()">
                            <option value="">Любая сухость</option>
                            <option value="Сухое">Сухое</option>
                            <option value="Полусухое">Полусухое</option>
                            <option value="Полусладкое">Полусладкое</option>
                            <option value="Сладкое">Сладкое / Крепленое</option>
                        </select>

                        <select id="cat-filter-region" class="cat-select" onchange="triggerCatalogReload()">
                            <option value="">Все регионы</option>
                            <option value="Кубань">Кубань</option>
                            <option value="Крым">Крым</option>
                            <option value="Долина Дона">Долина Дона</option>
                            <option value="Дагестан">Дагестан</option>
                            <option value="Нижняя Волга">Нижняя Волга</option>
                        </select>

                        <select id="cat-filter-grape" class="cat-select" onchange="triggerCatalogReload()">
                            <option value="">Все сорта</option>
                            <option value="Каберне">Каберне Совиньон / Фран</option>
                            <option value="Мерло">Мерло</option>
                            <option value="Саперави">Саперави</option>
                            <option value="Красностоп">Красностоп</option>
                            <option value="Шардоне">Шардоне</option>
                            <option value="Рислинг">Рислинг</option>
                            <option value="Совиньон">Совиньон Блан</option>
                            <option value="Мускат">Мускат</option>
                            <option value="Пино Нуар">Пино Нуар</option>
                        </select>

                        <select id="cat-filter-winery" class="cat-select" onchange="triggerCatalogReload()">
                            <option value="">Все винодельни</option>
                            <option value="Литавщук">Литавщук</option>
                            <option value="Фанагория">Фанагория</option>
                            <option value="Ведерниковъ">Ведерниковъ</option>
                            <option value="Массандра">Массандра</option>
                            <option value="Мысхако">Мысхако</option>
                            <option value="Абрау-Дюрсо">Абрау-Дюрсо</option>
                            <option value="Сикоры">Имение Сикоры</option>
                            <option value="Шато де Талю">Шато де Талю</option>
                            <option value="Гай-Кодзор">Гай-Кодзор</option>
                            <option value="Новый Свет">Новый Свет</option>
                        </select>

                        <select id="cat-filter-dish" class="cat-select" onchange="triggerCatalogReload()">
                            <option value="">Гастросочетания</option>
                            <option value="steak">BBQ, стейки и гриль</option>
                            <option value="fish">Рыба и морепродукты</option>
                            <option value="poultry">Блюда из птицы</option>
                            <option value="cheese">Сыры и брускетты</option>
                            <option value="dessert">Выпечка и десерты</option>
                        </select>

                        <select id="cat-filter-rating" class="cat-select" onchange="triggerCatalogReload()">
                            <option value="">Любой рейтинг</option>
                            <option value="4.8">от 4.8 (Топ вин)</option>
                            <option value="4.5">от 4.5 (Высокий)</option>
                        </select>
                    </div>"""

assert target in html, "target not found in scanner.html"
html = html.replace(target, replacement, 1)

# 3. Bump cache-busting version
html = html.replace('scanner.css?v=41_nocart', 'scanner.css?v=42_cathead', 1)
html = html.replace('scanner.js?v=36_nocart', 'scanner.js?v=37_cathead', 1)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated scanner.html successfully!")
