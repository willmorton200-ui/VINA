import re

with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Reset scroll restoration to manual and ensure always top at initial script execution
scroll_top_init = '''
    <script>
        // При загрузке страницы по умолчанию всегда показывать сверху (отключение скролла браузера)
        if ('scrollRestoration' in history) {
            history.scrollRestoration = 'manual';
        }
        window.scrollTo(0, 0);
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
'''
html = html.replace('    <script>\n        (function() {', scroll_top_init + '        (function() {', 1)

# 2. In switchHubTab, ensure window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
old_tab_scroll = "if (tabName !== 'catalog') {\n                closeWineDetail();\n            }"
new_tab_scroll = "if (tabName !== 'catalog') {\n                closeWineDetail();\n            }\n            window.scrollTo({ top: 0, left: 0, behavior: 'instant' });"
html = html.replace(old_tab_scroll, new_tab_scroll, 1)

# 3. Add profile horizontal feeds in #hub-panel-profile
old_profile_card = '''                <div class="hub-card" style="padding: 20px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                        <div>
                            <div style="font-size: 13px; color: #6c757d;">Бонусный баланс</div>
                            <div style="font-size: 24px; font-weight: 700; color: var(--primary);" id="profile-bonus-val">101 бонус</div>
                        </div>
                        <img src="znak.png" alt="Свое вино" style="width: 44px; height: 44px; border-radius: 50%;">
                    </div>
                    <div style="font-size: 14px; color: #495057; margin-bottom: 18px;" id="profile-phone-val">Телефон: не указан</div>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <button type="button" class="btn btn-primary" onclick="switchHubTab('sommelier')" style="border-radius: 10px; padding: 12px;">Винный Сомелье и Мастер тостов</button>
                        <button type="button" class="btn btn-secondary" onclick="openCameraFromHome()" style="border-radius: 10px; padding: 12px;">Открыть камеру сканера</button>
                        <button type="button" class="btn btn-secondary" onclick="restartOnboardingDemonstration()" style="border-radius: 10px; padding: 12px;">Повторить демонстрацию заставок</button>
                        <button type="button" class="btn btn-secondary" onclick="if(window.openBridgeSettings) window.openBridgeSettings();" style="border-radius: 10px; padding: 12px;">Настройки подключения к серверу</button>
                    </div>
                </div>'''

new_profile_card = '''                <div class="hub-card" style="padding: 20px; margin-bottom: 22px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
                        <div>
                            <div style="font-size: 13px; color: #6c757d;">Бонусный баланс</div>
                            <div style="font-size: 24px; font-weight: 700; color: #722F37;" id="profile-bonus-val">101 бонус</div>
                        </div>
                        <img src="znak.png" alt="Свое вино" style="width: 44px; height: 44px; border-radius: 50%;">
                    </div>
                    <div style="font-size: 14px; color: #495057; margin-bottom: 18px;" id="profile-phone-val">Телефон: не указан</div>
                    <div style="display: flex; flex-direction: column; gap: 10px;">
                        <button type="button" class="btn btn-primary" onclick="switchHubTab('sommelier')" style="border-radius: 10px; padding: 12px; background: #722F37;">Винный Сомелье и Мастер тостов</button>
                        <button type="button" class="btn btn-secondary" onclick="openCameraFromHome()" style="border-radius: 10px; padding: 12px;">Открыть камеру сканера</button>
                        <button type="button" class="btn btn-secondary" onclick="restartOnboardingDemonstration()" style="border-radius: 10px; padding: 12px;">Повторить демонстрацию заставок</button>
                        <button type="button" class="btn btn-secondary" onclick="if(window.openBridgeSettings) window.openBridgeSettings();" style="border-radius: 10px; padding: 12px;">Настройки подключения к серверу</button>
                    </div>
                </div>

                <!-- 1. Горизонтальная лента: Просмотренные вина -->
                <div class="profile-section-block" style="margin-bottom: 24px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <h3 class="home-section-title" style="margin: 0; font-size: 18px;">Просмотренные вина</h3>
                        <span style="font-size: 13px; color: #6c757d; font-weight: 600;" id="profile-viewed-count"></span>
                    </div>
                    <div class="home-popular-scroll" id="profile-viewed-wines-scroll">
                        <!-- Заполняется функцией renderProfileWines() -->
                    </div>
                </div>

                <!-- 2. Горизонтальная лента: Купленные вина -->
                <div class="profile-section-block" style="margin-bottom: 24px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                        <h3 class="home-section-title" style="margin: 0; font-size: 18px;">Купленные вина</h3>
                        <span style="font-size: 13px; color: #6c757d; font-weight: 600;" id="profile-bought-count"></span>
                    </div>
                    <div class="home-popular-scroll" id="profile-bought-wines-scroll">
                        <!-- Заполняется функцией renderProfileWines() -->
                    </div>
                </div>'''

if old_profile_card in html:
    html = html.replace(old_profile_card, new_profile_card)

# 4. Map: Replace green dashed route with burgundy, remove emojis, large full glasses from rating
old_map_stores_render = '''                listEl.innerHTML = (data.stores || []).map((s, idx) => {
                    bounds.push([s.lat, s.lon]);
                    const m = L.marker([s.lat, s.lon]).addTo(osmMapInstance)
                        .bindPopup(`<b>${idx + 1}. ${s.name}</b><br>${s.address}<br>🚶 ${s.distance_meters} м (~${s.walk_time_minutes} мин)<br>Цена: <b>${s.price_rub} ₽</b>`);
                    storeLeafletMarkers.push(m);

                    return `
                        <div class="store-card-row" id="store-row-${s.store_id}">
                            <div>
                                <div class="store-card-name">${idx + 1}. ${s.name}</div>
                                <div class="store-card-addr">${s.address} • 🕒 ${s.working_hours}</div>
                                <div class="store-card-meta">
                                    🚶 <b>${s.distance_meters} м</b> (~${s.walk_time_minutes} мин пешком) • В наличии: ${s.bottles_left} бут. (${s.price_rub} ₽)
                                </div>
                            </div>
                            <button class="btn-store-route" onclick="startWalkingNavigation(${s.lat}, ${s.lon}, '${s.name.replace(/'/g, "")}', '${s.store_id}')">
                                🚶 Путь
                            </button>
                        </div>
                    `;
                }).join('');'''

new_map_stores_render = '''                listEl.innerHTML = (data.stores || []).map((s, idx) => {
                    bounds.push([s.lat, s.lon]);

                    // Места винных магазинов на карте отмечаем полными бокалами (иконка большая из оценки) + номер + название
                    const storeIcon = L.divIcon({
                        className: 'vina-map-glass-marker',
                        html: `
                            <div class="vina-map-marker-inner" id="map-pin-${s.store_id}">
                                <div class="vina-marker-glass-wrap">
                                    <img src="img/glass_filled_straight.png" class="vina-marker-glass-icon" alt="">
                                    <span class="vina-marker-badge-num">${idx + 1}</span>
                                </div>
                                <div class="vina-marker-label-name">${s.name}</div>
                            </div>
                        `,
                        iconSize: [120, 68],
                        iconAnchor: [60, 50]
                    });

                    const m = L.marker([s.lat, s.lon], { icon: storeIcon }).addTo(osmMapInstance)
                        .bindPopup(`<b>${idx + 1}. ${s.name}</b><br>${s.address}<br>${s.distance_meters} м (~${s.walk_time_minutes} мин пешком)<br>В наличии: <b>${s.bottles_left} бут.</b> · Цена: <b>${s.price_rub} ₽</b>`);
                    storeLeafletMarkers.push(m);

                    return `
                        <div class="store-card-row" id="store-row-${s.store_id}">
                            <div>
                                <div class="store-card-name">${idx + 1}. ${s.name}</div>
                                <div class="store-card-addr">${s.address} • ${s.working_hours}</div>
                                <div class="store-card-meta">
                                    <b>${s.distance_meters} м</b> (~${s.walk_time_minutes} мин пешком) • В наличии: ${s.bottles_left} бут. (${s.price_rub} ₽)
                                </div>
                            </div>
                            <button class="btn-store-route" onclick="startWalkingNavigation(${s.lat}, ${s.lon}, '${s.name.replace(/'/g, "")}', '${s.store_id}')">
                                Путь
                            </button>
                        </div>
                    `;
                }).join('');'''

if old_map_stores_render in html:
    html = html.replace(old_map_stores_render, new_map_stores_render)

# User location marker on map with znak.png
old_user_marker = '''                if (userLocationMarker && osmMapInstance) osmMapInstance.removeLayer(userLocationMarker);
                userLocationMarker = L.circleMarker([userLatitude, userLongitude], {
                    radius: 9, color: '#ffffff', weight: 3, fillColor: '#28a745', fillOpacity: 1
                }).addTo(osmMapInstance).bindPopup('<b>🏠 Вы здесь</b>');'''

new_user_marker = '''                if (userLocationMarker && osmMapInstance) osmMapInstance.removeLayer(userLocationMarker);
                const userIcon = L.divIcon({
                    className: 'vina-map-user-marker',
                    html: `
                        <div class="vina-user-marker-inner">
                            <img src="znak.png" class="vina-user-znak-img" alt="">
                            <span class="vina-user-text">Вы здесь</span>
                        </div>
                    `,
                    iconSize: [95, 30],
                    iconAnchor: [47, 15]
                });
                userLocationMarker = L.marker([userLatitude, userLongitude], { icon: userIcon }).addTo(osmMapInstance)
                    .bindPopup('<b>Вы здесь</b>');'''

if old_user_marker in html:
    html = html.replace(old_user_marker, new_user_marker)

# Polyline color to burgundy #722F37
html = html.replace(
    "walkingPolyline = L.polyline(latlngs, { color: '#28a745', weight: 6, dashArray: '8, 6' }).addTo(osmMapInstance);",
    "walkingPolyline = L.polyline(latlngs, { color: '#722F37', weight: 6, dashArray: '8, 6' }).addTo(osmMapInstance);"
)

# HUD titles clean of emojis
html = html.replace(
    "document.getElementById('walk-hud-title').innerText = `🚶 Идем пешком в: ${shopName}`;",
    "document.getElementById('walk-hud-title').innerText = `Идем пешком в: ${shopName}`;"
)
html = html.replace(
    "lbl.innerHTML = `🍷 Выбрано: <b>${data.selected_wine_name}</b> — в наличии в 5 магазинах пешком`;",
    "lbl.innerHTML = `Выбрано: <b>${data.selected_wine_name}</b> — в наличии в 5 магазинах пешком`;"
)

# 5. Add "В корзину" button on renderHomeWineCard (Home, Favorites, Profile)
old_render_home_card = '''            return `
                <div class="home-wine-card" onclick="openWineDetailFromHome('${w.slug}')">
                    <div class="home-wine-card-top">
                        <div class="home-wine-rating-pill">
                            <span class="home-rating-glass">🍷</span>
                            <span class="home-rating-score">${w.rating}</span>
                            <span class="home-rating-reviews">(${w.reviews})</span>
                        </div>
                        <button type="button" class="home-fav-btn ${isFav ? 'is-fav' : ''}" data-slug="${w.slug}" onclick="toggleWineFavorite(event, '${w.slug}')" aria-label="В избранное">
                            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                            </svg>
                        </button>
                    </div>
                    <div class="home-wine-card-img-wrap">
                        <img src="${imgSrc}" alt="${w.title}" class="home-wine-card-img" loading="lazy">
                    </div>
                    <div class="home-wine-card-title">${w.title}</div>
                    <div class="home-wine-card-meta">${w.meta}</div>
                    <div class="home-wine-card-price">${w.price} ₽</div>
                </div>
            `;'''

new_render_home_card = '''            const priceNum = parseInt(String(w.price).replace(/\\D/g, '')) || 2090;
            return `
                <div class="home-wine-card" onclick="openWineDetailFromHome('${w.slug}')">
                    <div class="home-wine-card-top">
                        <div class="home-wine-rating-pill">
                            <span class="home-rating-glass">🍷</span>
                            <span class="home-rating-score">${w.rating}</span>
                            <span class="home-rating-reviews">(${w.reviews})</span>
                        </div>
                        <button type="button" class="home-fav-btn ${isFav ? 'is-fav' : ''}" data-slug="${w.slug}" onclick="toggleWineFavorite(event, '${w.slug}')" aria-label="В избранное">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                            </svg>
                        </button>
                    </div>
                    <div class="home-wine-card-img-wrap">
                        <img src="${imgSrc}" alt="${w.title}" class="home-wine-card-img" loading="lazy">
                    </div>
                    <div class="home-wine-card-title" title="${w.title}">${w.title}</div>
                    <div class="home-wine-card-meta">${w.meta}</div>
                    <div class="home-wine-card-bottom-row">
                        <div class="home-wine-card-price">${w.price} ₽</div>
                        <button type="button" class="btn-card-add-cart" onclick="event.stopPropagation(); addWineToCartDirectly('${w.slug}', '${w.title.replace(/'/g, "\\\\'")}', ${priceNum}, '${imgSrc}', '${w.meta.replace(/'/g, "\\\\'")}')" title="Добавить в корзину">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M5 7h14l-1 13H6L5 7z"></path>
                                <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                            </svg>
                            <span>В корзину</span>
                        </button>
                    </div>
                </div>
            `;'''

if old_render_home_card in html:
    html = html.replace(old_render_home_card, new_render_home_card)

# 6. Catalog cards: formatted like on the main screen (home-wine-card), strictly 2 per row
old_catalog_card_map = '''                    return `
                        <div class="catalog-wine-card" onclick="openWineDetail('${w.slug}')">
                            <div class="wine-bottle-box">
                                <div class="catalog-rating-badge">
                                    <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> ${ratingScore}
                                </div>
                                ${w.has_history ? `<div class="catalog-history-badge" onclick="event.stopPropagation(); openWineHistoryModal('${w.slug}')"><img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> История</div>` : ''}
                                <img src="${photoUrl}" alt="${w.name}" class="catalog-bottle-img" loading="lazy" onerror="this.src='badge_glass.png'">
                            </div>

                            <div>
                                <h4 class="catalog-wine-title" title="${w.name}">${w.name}</h4>
                                <div class="catalog-wine-producer">${wineryName}</div>
                                <div class="catalog-wine-tags">
                                    <span class="cat-tag-pill">${colorTag}</span>
                                    <span class="cat-tag-pill">${sugarTag}</span>
                                    <span class="cat-tag-pill">${regionTag}</span>
                                </div>
                                <div class="catalog-wine-price">${price.toLocaleString('ru-RU')} ₽</div>
                            </div>

                            <div class="catalog-card-actions">
                                <button class="btn-cat-map" onclick="event.stopPropagation(); openMapForWine('${w.slug}')">
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px; vertical-align: middle;">
                                        <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
                                        <line x1="8" y1="2" x2="8" y2="18"></line>
                                        <line x1="16" y1="6" x2="16" y2="22"></line>
                                    </svg>
                                    Карта
                                </button>
                                <button class="btn-cat-somm" onclick="event.stopPropagation(); openSommelierForWine('${w.slug}')">
                                    <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" style="margin-right: 4px; vertical-align: middle;" alt="">
                                    Сомелье
                                </button>
                            </div>
                        </div>
                    `;'''

new_catalog_card_map = '''                    const favs = getFavoriteSlugsSet();
                    const isFav = favs.has(w.slug);
                    const metaFormatted = [regionTag, colorTag && sugarTag ? `${colorTag}, ${sugarTag.toLowerCase()}` : (colorTag || sugarTag), '0.75 л'].filter(Boolean).join(', ');

                    return `
                        <div class="home-wine-card" onclick="openWineDetail('${w.slug}')" style="flex: auto; width: 100%;">
                            <div class="home-wine-card-top">
                                <div class="home-wine-rating-pill">
                                    <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="" style="width: 14px; height: 16px; object-fit: contain;">
                                    <span class="home-rating-score">${ratingScore}</span>
                                </div>
                                <button type="button" class="home-fav-btn ${isFav ? 'is-fav' : ''}" data-slug="${w.slug}" onclick="toggleWineFavorite(event, '${w.slug}')" aria-label="В избранное">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                                    </svg>
                                </button>
                            </div>
                            <div class="home-wine-card-img-wrap">
                                <img src="${photoUrl}" alt="${w.name}" class="home-wine-card-img" loading="lazy" onerror="this.src='badge_glass.png'">
                            </div>
                            <div class="home-wine-card-title" title="${w.name}">${w.name}</div>
                            <div class="home-wine-card-meta">${metaFormatted}</div>
                            <div class="home-wine-card-bottom-row">
                                <div class="home-wine-card-price">${price.toLocaleString('ru-RU')} ₽</div>
                                <button type="button" class="btn-card-add-cart" onclick="event.stopPropagation(); addWineToCartDirectly('${w.slug}', '${w.name.replace(/'/g, "\\\\'")}', ${price}, '${photoUrl}', '${metaFormatted.replace(/'/g, "\\\\'")}')" title="Добавить в корзину">
                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M5 7h14l-1 13H6L5 7z"></path>
                                        <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                                    </svg>
                                    <span>В корзину</span>
                                </button>
                            </div>
                        </div>
                    `;'''

if old_catalog_card_map in html:
    html = html.replace(old_catalog_card_map, new_catalog_card_map)

# 7. Add Profile Viewed & Bought Wines Logic
profile_render_script = '''
        // Логика профиля: лента просмотренных и лента купленных вин
        function trackViewedWine(slug, wineObj) {
            try {
                let viewed = JSON.parse(localStorage.getItem('svoe_vino_viewed_wines') || '[]');
                viewed = viewed.filter(w => w.slug !== slug);
                viewed.unshift({
                    slug: slug,
                    title: (wineObj && (wineObj.name || wineObj.title)) || 'Вино',
                    price: (wineObj && wineObj.price) || '2 090',
                    meta: (wineObj && wineObj.meta) || 'Россия · 0.75 л',
                    rating: (wineObj && wineObj.rating) || '4.6',
                    reviews: (wineObj && wineObj.reviews) || '15',
                    time: Date.now()
                });
                if (viewed.length > 20) viewed = viewed.slice(0, 20);
                localStorage.setItem('svoe_vino_viewed_wines', JSON.stringify(viewed));
            } catch(e) {}
        }

        function renderProfileWines() {
            const viewedScroll = document.getElementById('profile-viewed-wines-scroll');
            const boughtScroll = document.getElementById('profile-bought-wines-scroll');
            const viewedCountEl = document.getElementById('profile-viewed-count');
            const boughtCountEl = document.getElementById('profile-bought-count');

            let viewed = [];
            try { viewed = JSON.parse(localStorage.getItem('svoe_vino_viewed_wines') || '[]'); } catch(e) {}
            if (!viewed || viewed.length === 0) {
                viewed = [
                    HOME_POPULAR_ROW_1[0],
                    HOME_POPULAR_ROW_1[1],
                    HOME_POPULAR_ROW_2[0],
                    HOME_POPULAR_ROW_2[1]
                ].filter(Boolean);
            }

            if (viewedScroll) {
                if (viewedCountEl) viewedCountEl.textContent = `${viewed.length} вин`;
                viewedScroll.innerHTML = viewed.map(renderHomeWineCard).join('');
            }

            let bought = [];
            try { bought = JSON.parse(localStorage.getItem('svoe_vino_bought_wines') || '[]'); } catch(e) {}
            if (!bought || bought.length === 0) {
                bought = [
                    {
                        slug: 'loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131',
                        title: 'Вино Loco Cimbali Blanc de Neige, 2023',
                        meta: 'Россия, Крым, белое, сухое, 0.75 л',
                        price: '2 090',
                        rating: '4.6',
                        reviews: '441'
                    },
                    {
                        slug: 'abrau-durso-victor-dravigny-rozovoe-brut-130',
                        title: 'Игристое вино Абрау-Дюрсо Victor Dravigny',
                        meta: 'Россия, Кубань, розовое, брют, 0.75 л',
                        price: '1 890',
                        rating: '4.7',
                        reviews: '312'
                    }
                ];
            }

            if (boughtScroll) {
                if (boughtCountEl) boughtCountEl.textContent = `${bought.length} заказа`;
                boughtScroll.innerHTML = bought.map(renderHomeWineCard).join('');
            }
        }
'''

if 'function renderProfileWines()' not in html:
    html = html.replace('function switchHubTab(tabName) {', profile_render_script + '\n        function switchHubTab(tabName) {')

# Hook renderProfileWines into switchHubTab('profile')
html = html.replace(
    "if (phEl && ph) phEl.textContent = 'Телефон: +' + ph;\n                }",
    "if (phEl && ph) phEl.textContent = 'Телефон: +' + ph;\n                    renderProfileWines();\n                }"
)

# Hook trackViewedWine into openWineDetail(slug)
html = html.replace(
    "window.currentDetailWineSlug = slug;\n            document.body.style.overflow = '';",
    "window.currentDetailWineSlug = slug;\n            document.body.style.overflow = '';\n            trackViewedWine(slug, { name: slug, price: '2 090' });"
)

# Hook addWineToCartDirectly fallback into scanner.html if scanner.js hasn't loaded yet
cart_direct_fallback = '''
        function addWineToCartDirectly(slug, title, price, img, meta) {
            if (typeof window.addWineToCartDirectly === 'function') {
                return window.addWineToCartDirectly(slug, title, price, img, meta);
            }
        }
'''
if 'function addWineToCartDirectly' not in html:
    html = html.replace('function addCurrentDetailWineToCart(customSlug, customWine) {', cart_direct_fallback + '\n        function addCurrentDetailWineToCart(customSlug, customWine) {')

# Add preview_step=profile support in URL params
html = html.replace(
    "previewStep === 'wine_detail_zoomed_2x'",
    "previewStep === 'wine_detail_zoomed_2x' || previewStep === 'profile' || previewStep === 'cart_with_items'"
)

html = html.replace(
    "} else if (pStep === 'toasts') {",
    "} else if (pStep === 'profile') {\n                switchHubTab('profile');\n            } else if (pStep === 'cart_with_items') {\n                if (typeof window.ensureSampleCartItem === 'function') window.ensureSampleCartItem();\n                switchHubTab('cart');\n            } else if (pStep === 'toasts') {"
)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('Updated static/scanner.html')
