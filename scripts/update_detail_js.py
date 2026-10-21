import re

with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace openWineDetail and closeWineDetail and initDetailRating
old_js_start = "// 5. РЕЖИМ ПРОСМОТРА ВИНА ИЗ КАТАЛОГА (WINE DETAIL VIEW)"
old_js_end = "// 6. МОДАЛЬНОЕ ОКНО НЕДОСТАЮЩЕГО ВИНА"

new_js = """// 5. РЕЖИМ ПРОСМОТРА ВИНА ИЗ КАТАЛОГА (WINE DETAIL VIEW)
        // =====================================================================
        window.currentDetailWineSlug = null;
        window.currentDetailWinePrice = 2090;

        function renderGlassesStripHtml(score) {
            const s = Math.max(0, Math.min(5, parseFloat(score) || 0));
            let html = '';
            for (let i = 1; i <= 5; i++) {
                if (i <= Math.floor(s)) {
                    html += `<img src="img/glass_filled_straight.png" class="strip-glass-icon filled" alt="" style="width: 17px; height: 23px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%);">`;
                } else if (i === Math.ceil(s) && (s % 1 >= 0.25)) {
                    html += `<img src="img/glass_filled_straight.png" class="strip-glass-icon filled" alt="" style="width: 17px; height: 23px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%); opacity: 0.8;">`;
                } else {
                    html += `<img src="img/glass_empty_straight.png" class="strip-glass-icon empty" alt="" style="width: 17px; height: 23px; object-fit: contain; opacity: 0.45; filter: grayscale(100%);">`;
                }
            }
            return html;
        }

        function shareCurrentWine() {
            const title = document.getElementById('detail-wine-title')?.textContent || 'Свое вино';
            const slug = window.currentDetailWineSlug || '';
            const shareUrl = window.location.origin + window.location.pathname + '?preview_step=wine_detail&wine=' + encodeURIComponent(slug);
            if (navigator.share) {
                navigator.share({
                    title: `Вино «${title}» — Свое вино`,
                    text: `Посмотрите карточку вина «${title}» в приложении «Свое вино»:`,
                    url: shareUrl
                }).catch(() => {});
            } else if (navigator.clipboard) {
                navigator.clipboard.writeText(shareUrl).then(() => {
                    alert('Ссылка на вино скопирована в буфер обмена!');
                }).catch(() => {
                    prompt('Скопируйте ссылку на вино:', shareUrl);
                });
            } else {
                prompt('Скопируйте ссылку на вино:', shareUrl);
            }
        }

        function toggleCurrentDetailFavorite() {
            if (!window.currentDetailWineSlug) return;
            const isNowFav = toggleFavoriteSlug(window.currentDetailWineSlug);
            const btn = document.getElementById('detail-wine-fav-btn');
            if (btn) btn.classList.toggle('is-fav', isNowFav);
            updateFavBadge();
        }

        function updateDetailFavState(slug) {
            const btn = document.getElementById('detail-wine-fav-btn');
            if (btn) {
                const favs = getFavoriteSlugsSet();
                btn.classList.toggle('is-fav', favs.has(slug));
            }
        }

        function addCurrentDetailWineToCart() {
            if (!window.currentDetailWineSlug) return;
            let cart = [];
            try {
                cart = JSON.parse(localStorage.getItem('vina_cart') || '[]');
            } catch(e) { cart = []; }

            const slug = window.currentDetailWineSlug;
            const existing = cart.find(item => item.slug === slug);
            if (existing) {
                existing.qty = (existing.qty || 1) + 1;
            } else {
                const title = document.getElementById('detail-wine-title')?.textContent || 'Вино';
                const price = window.currentDetailWinePrice || 2090;
                cart.push({ slug: slug, title: title, price: price, qty: 1 });
            }
            try {
                localStorage.setItem('vina_cart', JSON.stringify(cart));
            } catch(e) {}

            updateCartBadge();

            const btn = document.getElementById('btn-detail-sticky-cart');
            const label = document.getElementById('detail-sticky-cart-label');
            if (btn && label) {
                btn.classList.add('added');
                label.textContent = '✓ Добавлено в корзину';
                setTimeout(() => {
                    btn.classList.remove('added');
                    label.textContent = 'Добавить в корзину';
                }, 1600);
            }
        }

        function updateCartBadge() {
            let count = 0;
            try {
                const cart = JSON.parse(localStorage.getItem('vina_cart') || '[]');
                count = cart.reduce((acc, it) => acc + (it.qty || 1), 0);
            } catch(e) {}
            const badge = document.getElementById('bnav-cart-badge');
            if (badge) {
                if (count > 0) {
                    badge.textContent = count;
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }
            }
        }

        function openSommelierForDetailWine() {
            if (window.currentDetailWineSlug) {
                openSommelierForWine(window.currentDetailWineSlug);
            }
        }

        async function openWineDetail(slug) {
            const mainView = document.getElementById('catalog-main-view');
            const detailView = document.getElementById('catalog-detail-view');
            if (!detailView) return;

            window.currentDetailWineSlug = slug;

            // Переключаем шапку: скрываем бренд, показываем Артикул + Поделиться
            const brandEl = document.getElementById('header-center-brand');
            const detailHdrEl = document.getElementById('header-center-detail');
            const stickyBar = document.getElementById('detail-sticky-action-bar');
            if (brandEl) brandEl.style.display = 'none';
            if (detailHdrEl) detailHdrEl.style.display = 'flex';
            if (stickyBar) stickyBar.classList.add('visible');

            // Артикул (вычисляем стабильный 6-значный артикул от слага)
            const artNum = Math.abs(slug.split('').reduce((acc, c) => (acc << 5) - acc + c.charCodeAt(0), 0)) % 900000 + 100000;
            const artEl = document.getElementById('detail-header-article');
            if (artEl) artEl.textContent = 'Арт. ' + artNum;

            if (mainView) mainView.style.display = 'none';
            detailView.style.display = 'block';
            window.scrollTo({ top: 0, behavior: 'smooth' });

            document.getElementById('detail-wine-title').textContent = 'Загрузка карточки вина...';
            document.getElementById('detail-wine-winery').textContent = '';
            document.getElementById('detail-wine-description').textContent = '';
            document.getElementById('detail-wine-img').src = `${getHubApiBase()}/api/image/${slug}`;
            document.getElementById('detail-wine-history-block').style.display = 'none';
            document.getElementById('detail-history-pill-top').innerHTML = '';

            updateDetailFavState(slug);

            try {
                let wineData = null;
                let fullData = null;
                try {
                    const res = await fetch(`${getHubApiBase()}/api/v2/wine/${slug}/full-sommelier`);
                    if (res.ok) {
                        fullData = await res.json();
                        wineData = fullData.wine;
                    }
                } catch(e) { console.warn(e); }

                if (!wineData) {
                    try {
                        const res = await fetch(`${getHubApiBase()}/api/wine/${slug}`);
                        if (res.ok) wineData = await res.json();
                    } catch(e) {}
                }

                // Фоллбэк из локального списка популярных вин при открытии офлайн/статически
                if (!wineData) {
                    const allLocal = [...HOME_POPULAR_ROW_1, ...HOME_POPULAR_ROW_2];
                    const found = allLocal.find(w => w.slug === slug);
                    if (found) {
                        wineData = {
                            name: found.title,
                            winery: found.title.includes(' ') ? found.title.split(' ')[0] : 'Винодельня России',
                            alcohol: '13.1% об.',
                            color: found.meta.includes('белое') ? 'Белое' : (found.meta.includes('розовое') ? 'Розовое' : 'Красное'),
                            sweetness: found.meta.includes('сухое') ? 'Сухое' : (found.meta.includes('брют') ? 'Брют' : 'Полусухое'),
                            region: found.meta.includes('Крым') ? 'Крым' : (found.meta.includes('Кубань') ? 'Кубань' : 'Россия'),
                            grape: 'Шардоне',
                            description: 'Изящное российское вино с гармоничным органолептическим профилем, минеральной свежестью и долгим выразительным послевкусием.',
                            rating: found.rating || '4.5',
                            price: found.price || 2090
                        };
                    } else {
                        wineData = {
                            name: slug.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                            winery: 'Винодельня России',
                            alcohol: '13.5% об.',
                            color: 'Вино',
                            sweetness: 'Сухое',
                            region: 'Россия',
                            grape: 'Классические сорта',
                            description: 'Аутентичное российское вино с богатым органолептическим букетом и гармоничным послевкусием.',
                            rating: '4.85',
                            price: 1990
                        };
                    }
                }

                window.currentDetailWinePrice = wineData.price || 2090;

                const wineTitle = wineData.name || wineData.title || slug;
                const wineryName = wineData.winery || (typeof wineTitle === 'string' && wineTitle.includes(' ') ? wineTitle.split(' ')[0] : 'Винодельня России');
                document.getElementById('detail-wine-title').textContent = wineTitle;
                document.getElementById('detail-wine-winery').textContent = wineryName;
                document.getElementById('detail-wine-alcohol').textContent = wineData.alcohol ? (String(wineData.alcohol).includes('об') ? wineData.alcohol : `${wineData.alcohol} об.`) : '13.1% об.';
                document.getElementById('detail-wine-color').textContent = wineData.color || 'Белое';
                document.getElementById('detail-wine-sugar').textContent = wineData.sugar || wineData.sweetness || 'Сухое';
                document.getElementById('detail-wine-region').textContent = wineData.region || 'Крым';
                document.getElementById('detail-wine-grape').textContent = wineData.grape ? (wineData.grape.startsWith('Сорт:') ? wineData.grape : `Сорт: ${wineData.grape}`) : 'Сорт: Шардоне';
                document.getElementById('detail-wine-description').textContent = wineData.description || 'Аутентичное российское вино с богатым органолептическим букетом и гармоничным послевкусием.';

                const score = wineData.rating ? parseFloat(wineData.rating).toFixed(1) : '4.5';
                const totalVotes = Math.max(12, Math.round((parseFloat(score) * 28) + (slug.length * 3)));
                
                const scoreBadge = document.getElementById('detail-badge-score');
                if (scoreBadge) scoreBadge.textContent = score.replace('.', ',');
                const votesBadge = document.getElementById('detail-badge-votes');
                if (votesBadge) votesBadge.textContent = totalVotes;

                const stripEl = document.getElementById('detail-glasses-strip');
                if (stripEl) stripEl.innerHTML = renderGlassesStripHtml(score);

                initDetailRating(slug);

                const hist = fullData ? fullData.history : null;
                const histBlock = document.getElementById('detail-wine-history-block');
                const histTopPill = document.getElementById('detail-history-pill-top');
                if (hist) {
                    histBlock.style.display = 'block';
                    document.getElementById('detail-wine-history-year').textContent = `Год создания: ${hist.creation_year}`;
                    document.getElementById('detail-wine-history-headline').textContent = hist.headline;
                    document.getElementById('detail-wine-history-text').textContent = hist.legend_summary;
                    
                    const evBox = document.getElementById('detail-wine-history-events');
                    if (evBox && hist.historical_events) {
                        evBox.innerHTML = hist.historical_events.map(ev => `
                            <div style="margin-top: 6px; padding: 8px 10px; background: rgba(255,255,255,0.7); border-radius: 8px; font-size: 12px; color: #333;">
                                <strong style="color: var(--primary);">${ev.era_year}: ${ev.title}</strong>
                                <div style="margin-top: 2px;">${ev.story}</div>
                            </div>
                        `).join('');
                    }
                    if (histTopPill) {
                        histTopPill.innerHTML = `
                            <span class="cat-chip gold-badge" onclick="openWineHistoryModal('${slug}')" style="cursor: pointer; padding: 6px 12px; font-size: 12px;">
                                <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt=""> История вина
                            </span>
                        `;
                    }
                } else {
                    histBlock.style.display = 'none';
                    if (histTopPill) histTopPill.innerHTML = '';
                }

                const organo = (fullData && fullData.organoleptic) ? fullData.organoleptic : {
                    acidity: 3.8, tannins: 3.5, body: 4.2, sweetness: 1.5, oak_intensity: 3.2
                };
                
                const acidity = Number(organo.acidity || 3.8);
                const tannins = Number(organo.tannins || 3.5);
                const body = Number(organo.body || 4.0);
                const sweetness = Number(organo.sweetness || 1.5);
                const oak = Number(organo.oak_intensity || 3.0);

                const items = [
                    { label: 'Кислотность', val: acidity, desc: acidity >= 3.8 ? 'Яркая, освежающая' : 'Мягкая, сглаженная' },
                    { label: 'Танинность', val: tannins, desc: tannins >= 3.5 ? 'Бархатные, структурные' : 'Шелковистые' },
                    { label: 'Тело / Плотность', val: body, desc: body >= 3.8 ? 'Полнотелое, глубокое' : 'Средняя плотность' },
                    { label: 'Сладость', val: sweetness, desc: sweetness >= 3.0 ? 'Десертное / Ликерное' : 'Сухое вино' },
                    { label: 'Выдержка в дубе', val: oak, desc: oak >= 3.5 ? 'Благородный дуб' : 'Легкая выдержка' },
                ];

                document.getElementById('detail-sensory-bars').innerHTML = `
                    <div class="sensory-bars-card" style="padding: 14px 16px; background: #ffffff; border: 1px solid #eef0f3; border-radius: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
                        ${items.map(it => {
                            const pct = Math.min(Math.max((it.val / 5.0) * 100, 5), 100);
                            return `
                                <div class="sensory-meter-row" style="margin-bottom: 11px;">
                                    <div class="sensory-meter-label" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                                        <span class="sensory-meter-name" style="font-size: 13px; font-weight: 500; color: #1a1a1a;">${it.label}</span>
                                        <span class="sensory-meter-val" style="font-size: 12px; font-weight: 700; color: var(--primary, #800020);">${it.val.toFixed(1)} / 5</span>
                                    </div>
                                    <div class="sensory-meter-track">
                                        <div class="sensory-meter-fill" style="width: ${pct}%;"></div>
                                    </div>
                                    <div style="font-size: 10px; color: #8e8e93; text-align: right; margin-top: 2px;">${it.desc}</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;

            } catch(err) {
                console.error(err);
                document.getElementById('detail-wine-title').textContent = 'Ошибка загрузки карточки вина';
            }
        }

        function closeWineDetail() {
            const mainView = document.getElementById('catalog-main-view');
            const detailView = document.getElementById('catalog-detail-view');
            if (detailView) detailView.style.display = 'none';
            if (mainView) mainView.style.display = 'block';

            // Возвращаем обычную шапку и скрываем нижнюю статическую панель
            const brandEl = document.getElementById('header-center-brand');
            const detailHdrEl = document.getElementById('header-center-detail');
            const stickyBar = document.getElementById('detail-sticky-action-bar');
            if (brandEl) brandEl.style.display = 'flex';
            if (detailHdrEl) detailHdrEl.style.display = 'none';
            if (stickyBar) stickyBar.classList.remove('visible');
        }

        function initDetailRating(slug) {
            const container = document.getElementById('detail-glasses-container');
            if (!container) return;

            const userRatingText = document.getElementById('detail-user-rating-text');
            const totalVotesEl = document.getElementById('detail-total-votes');
            const avgScoreEl = document.getElementById('detail-avg-score');
            const badgeScoreEl = document.getElementById('detail-badge-score');
            const badgeVotesEl = document.getElementById('detail-badge-votes');
            const stripEl = document.getElementById('detail-glasses-strip');

            let globalStats = JSON.parse(localStorage.getItem('vina_global_ratings')) || {};
            if (!globalStats[slug]) {
                globalStats[slug] = { total: 16, sum: 72 };
            }

            let currentRating = parseInt(localStorage.getItem('vina_rating_' + slug) || '0', 10);
            const slots = container.querySelectorAll('.glass-slot');

            function updateGlasses(rating) {
                const stats = globalStats[slug] || { total: 16, sum: 72 };
                const avg = (stats.sum / stats.total).toFixed(1);

                if (avgScoreEl) avgScoreEl.textContent = avg;
                if (totalVotesEl) totalVotesEl.textContent = stats.total;
                if (badgeScoreEl) badgeScoreEl.textContent = avg.replace('.', ',');
                if (badgeVotesEl) badgeVotesEl.textContent = stats.total;
                if (stripEl) stripEl.innerHTML = renderGlassesStripHtml(avg);

                if (userRatingText) {
                    userRatingText.textContent = rating > 0 ? `Ваша оценка: ${rating} из 5` : 'Ваша оценка: - из 5';
                }

                slots.forEach((slot, index) => {
                    const idx = index + 1;
                    const img = slot.querySelector('.glass-img');
                    if (idx <= rating) {
                        slot.classList.add('active-bg');
                        if (img) img.src = 'img/glass_filled_straight.png';
                    } else {
                        slot.classList.remove('active-bg');
                        if (img) img.src = 'img/glass_empty_straight.png';
                    }
                });
            }

            updateGlasses(currentRating);

            slots.forEach((slot, index) => {
                const idx = index + 1;

                slot.onmouseenter = () => {
                    slots.forEach((s, i) => {
                        if (i <= index) {
                            s.classList.add('active-bg');
                        } else if (i + 1 > currentRating) {
                            s.classList.remove('active-bg');
                        }
                    });
                };

                slot.onmouseleave = () => {
                    updateGlasses(currentRating);
                };

                const handleRate = (e) => {
                    if (e.type === 'touchend') e.preventDefault();
                    e.stopPropagation();

                    if (currentRating > 0) {
                        globalStats[slug].sum -= currentRating;
                    } else {
                        globalStats[slug].total += 1;
                    }

                    currentRating = idx;
                    globalStats[slug].sum += currentRating;

                    localStorage.setItem('vina_rating_' + slug, currentRating);
                    localStorage.setItem('vina_global_ratings', JSON.stringify(globalStats));

                    updateGlasses(currentRating);
                };

                slot.onclick = handleRate;
                slot.ontouchend = handleRate;
            });
        }
        """

start_pos = html.find(old_js_start)
end_pos = html.find(old_js_end)

if start_pos != -1 and end_pos != -1:
    html = html[:start_pos] + new_js + "\n        // =====================================================================\n        " + html[end_pos:]
    print("JS logic updated successfully")
else:
    print("Old JS boundaries not found:", start_pos, end_pos)

# Also ensure switchHubTab closes wine detail
switch_target = "if (tabName === 'catalog') {"
# In switchHubTab, if tabName != 'catalog', we ensure closeWineDetail() is called:
old_switch = """            if (tabName === 'scanner') {"""
new_switch = """            if (tabName !== 'catalog') {
                closeWineDetail();
            }

            if (tabName === 'scanner') {"""
if old_switch in html:
    html = html.replace(old_switch, new_switch, 1)
    print("switchHubTab updated to closeWineDetail")

# In DOMContentLoaded, add support for ?preview_step=wine_detail and updateCartBadge()
old_dcl = "initHomePopularRows();"
new_dcl = """initHomePopularRows();
            updateCartBadge();"""
if old_dcl in html:
    html = html.replace(old_dcl, new_dcl, 1)

old_prev = "} else if (pStep === 'scanner') {"
new_prev = """} else if (pStep === 'wine_detail') {
                switchHubTab('catalog');
                openWineDetail('loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131');
            } else if (pStep === 'scanner') {"""
if old_prev in html:
    html = html.replace(old_prev, new_prev, 1)
    print("DOMContentLoaded preview_step=wine_detail added")

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)
