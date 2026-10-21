import re

# 1. READ scanner.html
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# --- A. Remove Cart from Bottom Nav Bar ---
old_bnav_cart = """            <button type="button" class="bnav-item" id="bnav-cart" onclick="switchHubTab('cart')">
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

if old_bnav_cart in html:
    html = html.replace(old_bnav_cart, "")
    print("Removed bnav-cart from bottom nav bar")
else:
    print("WARNING: old_bnav_cart not found directly, trying regex")
    html = re.sub(r'<button[^>]*id="bnav-cart"[^>]*>.*?</button>\s*', '', html, flags=re.DOTALL)
    print("Removed bnav-cart via regex")

# --- B. Remove Hub Panel Cart ---
# Find <div id="hub-panel-cart" class="hub-panel"> ... </div>
cart_panel_match = re.search(r'<!--\s*=+\s*-->\s*<!--\s*СТРАНИЦА КОРЗИНА.*?-->\s*<div id="hub-panel-cart".*?</div>\s*</div>\s*</div>\s*(?=<!--\s*=+\s*-->\s*<!--\s*СТРАНИЦА ПРОФИЛЬ)', html, re.DOTALL)
if cart_panel_match:
    html = html[:cart_panel_match.start()] + html[cart_panel_match.end():]
    print("Removed hub-panel-cart successfully")
else:
    print("WARNING: hub-panel-cart match not found with comment header, trying direct panel regex")
    html = re.sub(r'<div id="hub-panel-cart" class="hub-panel">.*?</div>\s*</div>\s*</div>\s*(?=<!--\s*=+\s*-->\s*<!--\s*СТРАНИЦА ПРОФИЛЬ)', '', html, flags=re.DOTALL)

# --- C. Update sticky action bar in wine detail ---
old_sticky_bar = """        <!-- 8. Статический сектор выше нижней навигации: слева "Сомелье", справа "Добавить в корзину" (не двигается с лентой) -->
        <div class="detail-sticky-action-bar" id="detail-sticky-action-bar">
            <button type="button" class="btn-sticky-somm" id="btn-detail-sticky-somm" onclick="openSommelierForDetailWine()">
                <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="" style="width: 18px; height: 20px; object-fit: contain;">
                <span>Сомелье</span>
            </button>
            <button type="button" class="btn-sticky-cart" id="btn-detail-sticky-cart" onclick="addCurrentDetailWineToCart()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M5 7h14l-1 13H6L5 7z"></path>
                    <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                </svg>
                <span id="detail-sticky-cart-label">Добавить в корзину</span>
            </button>
        </div>"""

new_sticky_bar = """        <!-- 8. Статический сектор выше нижней навигации: слева "Сомелье", справа "Найти в магазинах" -->
        <div class="detail-sticky-action-bar" id="detail-sticky-action-bar">
            <button type="button" class="btn-sticky-somm" id="btn-detail-sticky-somm" onclick="openSommelierForDetailWine()">
                <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="" style="width: 18px; height: 20px; object-fit: contain;">
                <span>Спросить сомелье</span>
            </button>
            <button type="button" class="btn-sticky-map" id="btn-detail-sticky-map" onclick="findStoresForCurrentWine()">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                    <circle cx="12" cy="10" r="3"></circle>
                </svg>
                <span>Найти в магазинах</span>
            </button>
        </div>"""

if old_sticky_bar in html:
    html = html.replace(old_sticky_bar, new_sticky_bar)
    print("Updated detail-sticky-action-bar to Sommelier + Find in Stores")
else:
    print("WARNING: old_sticky_bar not found directly")

# --- D. Remove price and cart button from renderHomeWineCard ---
old_home_bottom = """                        <div class="home-wine-card-bottom-row">
                            <div class="home-wine-price">${(typeof w.price==='number'?w.price:parseInt(String(w.price).replace(/\\D/g,''),10)||2090).toLocaleString('ru-RU')} ₽</div>
                            <button type="button" class="btn-card-add-cart" onclick="event.stopPropagation(); addWineToCartDirectly('${w.slug}', this)" title="Добавить в корзину">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M5 7h14l-1 13H6L5 7z"></path>
                                    <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                                </svg>
                                <span>В корзину</span>
                            </button>
                        </div>"""

if old_home_bottom in html:
    html = html.replace(old_home_bottom, "")
    print("Removed price and cart button from renderHomeWineCard")
else:
    print("WARNING: old_home_bottom not found directly")

# --- E. Remove price and cart button from fetchCatalogWines ---
old_cat_bottom = """                                <div class="home-wine-card-bottom-row">
                                    <div class="home-wine-price">${price.toLocaleString('ru-RU')} ₽</div>
                                    <button type="button" class="btn-card-add-cart" onclick="event.stopPropagation(); addWineToCartDirectly('${w.slug}', this)" title="Добавить в корзину">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                            <path d="M5 7h14l-1 13H6L5 7z"></path>
                                            <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                                        </svg>
                                        <span>В корзину</span>
                                    </button>
                                </div>"""

if old_cat_bottom in html:
    html = html.replace(old_cat_bottom, "")
    print("Removed price and cart button from fetchCatalogWines")
else:
    print("WARNING: old_cat_bottom not found directly")

# --- F. Remove price from sommelier recommendations ---
old_somm_price = '<div style="text-align: right; font-weight: 700; color: var(--primary);">${a.price_rub || 990} ₽</div>'
if old_somm_price in html:
    html = html.replace(old_somm_price, '')
    print("Removed price from sommelier recommendations")

# --- G. Update switchHubTab to handle 'cart' gracefully and add findStoresForCurrentWine ---
old_switch_tab = """            const bnavMap = {
                home: 'bnav-home',
                toasts: 'bnav-home',
                scanner: 'bnav-home',
                map: 'bnav-home',
                catalog: 'bnav-catalog',
                cart: 'bnav-cart',
                favorites: 'bnav-favorites',
                profile: 'bnav-profile',
                sommelier: 'bnav-profile'
            };"""

new_switch_tab = """            if (tabName === 'cart') {
                tabName = 'catalog';
            }
            const bnavMap = {
                home: 'bnav-home',
                toasts: 'bnav-home',
                scanner: 'bnav-home',
                map: 'bnav-home',
                catalog: 'bnav-catalog',
                favorites: 'bnav-favorites',
                profile: 'bnav-profile',
                sommelier: 'bnav-profile'
            };"""

if old_switch_tab in html:
    html = html.replace(old_switch_tab, new_switch_tab)
    print("Updated switchHubTab")

# Add findStoresForCurrentWine if not present
if "function findStoresForCurrentWine" not in html:
    helper_code = """
        function findStoresForCurrentWine() {
            switchHubTab('map');
            setTimeout(function() {
                if (typeof load5NearbyWalkingStores === 'function') {
                    load5NearbyWalkingStores();
                }
            }, 300);
        }
        window.findStoresForCurrentWine = findStoresForCurrentWine;
    """
    html = html.replace("window.openSommelierForDetailWine = openSommelierForDetailWine;", "window.openSommelierForDetailWine = openSommelierForDetailWine;\n" + helper_code)
    print("Added findStoresForCurrentWine")

# --- H. Update preview steps to catalog instead of cart ---
html = re.sub(r"previewStep === 'cart' \|\| previewStep === 'cart_click_test' \|\| previewStep === 'cart_btn_feedback_test' \|\| previewStep === 'catalog_cart_click_test' \|\|", "", html)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("scanner.html updated successfully!")
