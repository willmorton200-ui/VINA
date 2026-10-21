with open('static/scanner.js', 'r', encoding='utf-8') as f:
    js = f.read()

target_start = "    // 4. РЕЖИМ ПРОСМОТРА ВИНА ИЗ КАТАЛОГА (WINE DETAIL VIEW)"
target_end = "    function initDetailRating(slug) {"

new_code = """    // 4. РЕЖИМ ПРОСМОТРА ВИНА ИЗ КАТАЛОГА (WINE DETAIL VIEW)
    // =========================================================================
    function renderGlassesStripHtml(score) {
        const s = Math.max(0, Math.min(5, parseFloat(score) || 0));
        let html = '';
        for (let i = 1; i <= 5; i++) {
            if (i <= Math.floor(s)) {
                html += '<img src="img/glass_filled_straight.png" class="strip-glass-icon filled" alt="" style="width: 17px; height: 23px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%);">';
            } else if (i === Math.ceil(s) && (s % 1 >= 0.25)) {
                html += '<img src="img/glass_filled_straight.png" class="strip-glass-icon filled" alt="" style="width: 17px; height: 23px; object-fit: contain; filter: brightness(0) saturate(100%) invert(11%) sepia(77%) saturate(4640%) hue-rotate(334deg) brightness(78%) contrast(106%); opacity: 0.8;">';
            } else {
                html += '<img src="img/glass_empty_straight.png" class="strip-glass-icon empty" alt="" style="width: 17px; height: 23px; object-fit: contain; opacity: 0.45; filter: grayscale(100%);">';
            }
        }
        return html;
    }

    window.openSommelierEntryPoint = function(slug, wineData) {
        console.log('[SOMMELIER ENTRY POINT] Точка входа модуля Сомелье активирована:', slug, wineData);
        if (typeof window.externalSommelierHandler === 'function') {
            window.externalSommelierHandler(slug, wineData);
            return;
        }
        const nameEl = document.getElementById('somm-stub-wine-name');
        if (nameEl) {
            const title = (wineData && (wineData.name || wineData.title)) ? (wineData.name || wineData.title) : (document.getElementById('detail-wine-title')?.textContent || slug || 'Вино');
            nameEl.textContent = title;
        }
        const modal = document.getElementById('sommelier-stub-modal');
        if (modal) modal.style.display = 'flex';
    };

    window.closeSommelierStubModal = function() {
        const modal = document.getElementById('sommelier-stub-modal');
        if (modal) modal.style.display = 'none';
    };

    window.openWineDetail = async function(slug) {
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

        // Артикул
        const artNum = Math.abs(slug.split('').reduce((acc, c) => (acc << 5) - acc + c.charCodeAt(0), 0)) % 900000 + 100000;
        const artEl = document.getElementById('detail-header-article');
        if (artEl) artEl.textContent = 'Арт. ' + artNum;

        if (mainView) mainView.style.display = 'none';
        detailView.style.display = 'block';
        window.scrollTo({ top: 0, behavior: 'smooth' });

        if (window.detailInspector) window.detailInspector.reset();

        document.getElementById('detail-wine-title').textContent = 'Загрузка карточки вина...';
        document.getElementById('detail-wine-winery').textContent = '';
        document.getElementById('detail-wine-description').textContent = '';
        document.getElementById('detail-wine-img').src = apiUrl(`/api/image/${slug}`);
        document.getElementById('detail-wine-history-block').style.display = 'none';
        const histTopPill = document.getElementById('detail-history-pill-top');
        if (histTopPill) histTopPill.innerHTML = '';

        if (typeof updateDetailFavState === 'function') {
            updateDetailFavState(slug);
        }

        try {
            let wineData = null;
            let fullData = null;
            try {
                const res = await fetch(apiUrl(`/api/v2/wine/${slug}/full-sommelier`));
                if (res.ok) {
                    fullData = await res.json();
                    wineData = fullData.wine;
                }
            } catch(e) { console.warn(e); }

            if (!wineData) {
                try {
                    const res = await fetch(apiUrl(`/api/wine/${slug}`));
                    if (res.ok) wineData = await res.json();
                } catch(e) {}
            }

            // Фоллбэк из локальных вин при открытии без запущенного бэкенда
            if (!wineData) {
                const localList = (window.HOME_POPULAR_ROW_1 || []).concat(window.HOME_POPULAR_ROW_2 || []);
                const found = localList.find(w => w.slug === slug);
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
                        name: 'Loco Cimbali Blanc de Neige',
                        winery: 'Loco Cimbali',
                        alcohol: '13.1% об.',
                        color: 'Белое',
                        sweetness: 'Сухое',
                        region: 'Крым',
                        grape: 'Шардоне',
                        description: 'Изящное российское вино с богатым органолептическим букетом и гармоничным послевкусием.',
                        rating: '4.5',
                        price: 2090
                    };
                }
            }

            window.currentDetailWinePrice = wineData.price || 2090;

            const wineTitle = wineData.name || wineData.title || slug;
            const wineryName = wineData.winery || (typeof wineTitle === 'string' && wineTitle.includes(' ') ? wineTitle.split(' ')[0] : 'Винодельня России');
            const titleEl = document.getElementById('detail-wine-title');
            if (titleEl) titleEl.textContent = wineTitle;

            const wineryEl = document.getElementById('detail-wine-winery');
            if (wineryEl) wineryEl.textContent = wineryName;

            const alcEl = document.getElementById('detail-wine-alcohol');
            if (alcEl) alcEl.textContent = wineData.alcohol ? (String(wineData.alcohol).includes('об') ? wineData.alcohol : `${wineData.alcohol} об.`) : '13.1% об.';

            const colEl = document.getElementById('detail-wine-color');
            if (colEl) colEl.textContent = wineData.color || 'Белое';

            const sugEl = document.getElementById('detail-wine-sugar');
            if (sugEl) sugEl.textContent = wineData.sugar || wineData.sweetness || 'Сухое';

            const regEl = document.getElementById('detail-wine-region');
            if (regEl) regEl.textContent = wineData.region || 'Крым';

            const grpEl = document.getElementById('detail-wine-grape');
            if (grpEl) grpEl.textContent = wineData.grape ? (wineData.grape.startsWith('Сорт:') ? wineData.grape : `Сорт: ${wineData.grape}`) : 'Сорт: Шардоне';

            const descEl = document.getElementById('detail-wine-description');
            if (descEl) descEl.textContent = wineData.description || 'Аутентичное российское вино с богатым органолептическим букетом и терруарным характером.';

            const score = wineData.rating ? parseFloat(wineData.rating).toFixed(1) : '4.5';
            const totalVotes = Math.max(12, Math.round((parseFloat(score) * 28) + (slug.length * 3)));
            
            const badgeScoreEl = document.getElementById('detail-badge-score');
            if (badgeScoreEl) badgeScoreEl.textContent = score.replace('.', ',');
            const badgeVotesEl = document.getElementById('detail-badge-votes');
            if (badgeVotesEl) badgeVotesEl.textContent = totalVotes;

            const stripEl = document.getElementById('detail-glasses-strip');
            if (stripEl) stripEl.innerHTML = renderGlassesStripHtml(score);

            initDetailRating(slug);

            const hist = fullData ? fullData.history : null;
            const histBlock = document.getElementById('detail-wine-history-block');
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
            const sensoryBox = document.getElementById('detail-sensory-bars');
            if (sensoryBox) sensoryBox.innerHTML = renderSensoryBarsHtml(organo);

            // Привязываем кнопки постоянной панели
            const btnStickySomm = document.getElementById('btn-detail-sticky-somm');
            if (btnStickySomm) {
                btnStickySomm.onclick = () => window.openSommelierEntryPoint(slug, wineData);
            }
            const btnStickyCart = document.getElementById('btn-detail-sticky-cart');
            if (btnStickyCart) {
                btnStickyCart.onclick = () => {
                    if (typeof window.addCurrentDetailWineToCart === 'function') {
                        window.addCurrentDetailWineToCart();
                    }
                };
            }

        } catch(err) {
            console.error(err);
            document.getElementById('detail-wine-title').textContent = 'Ошибка загрузки карточки вина';
        }
    };

    window.closeWineDetail = function() {
        const mainView = document.getElementById('catalog-main-view');
        const detailView = document.getElementById('catalog-detail-view');
        if (detailView) detailView.style.display = 'none';
        if (mainView) mainView.style.display = 'block';

        const brandEl = document.getElementById('header-center-brand');
        const detailHdrEl = document.getElementById('header-center-detail');
        const stickyBar = document.getElementById('detail-sticky-action-bar');
        if (brandEl) brandEl.style.display = 'flex';
        if (detailHdrEl) detailHdrEl.style.display = 'none';
        if (stickyBar) stickyBar.classList.remove('visible');
    };

"""

start_pos = js.find(target_start)
end_pos = js.find(target_end)

if start_pos != -1 and end_pos != -1:
    js = js[:start_pos] + new_code + "    " + js[end_pos:]
    print("scanner.js updated successfully")
else:
    print("scanner.js boundaries not found:", start_pos, end_pos)

with open('static/scanner.js', 'w', encoding='utf-8') as f:
    f.write(js)
