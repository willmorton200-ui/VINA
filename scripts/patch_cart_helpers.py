import re

with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update addWineToCartDirectly in scanner.html
old_code_html = """        function addWineToCartDirectly(slug, title, price, img, meta) {
            if (!slug) return;

            let finalTitle = title;
            let finalPrice = typeof price === 'number' ? price : (parseInt(String(price).replace(/\\D/g, ''), 10) || 0);
            let finalImg = img;
            let finalMeta = meta;

            // 1. Поиск данных в DOM карточки кликнутой кнопки
            const clickedBtn = (window.event && window.event.currentTarget) ? window.event.currentTarget : (window.event ? window.event.target : null);
            const card = clickedBtn ? clickedBtn.closest('.home-wine-card, .catalog-wine-card-2col, [data-slug]') : null;

            if (card) {
                if (!finalTitle) {
                    const tEl = card.querySelector('.home-wine-title');
                    if (tEl) finalTitle = tEl.textContent.trim();
                }
                if (!finalPrice) {
                    const pEl = card.querySelector('.home-wine-price');
                    if (pEl) finalPrice = parseInt(pEl.textContent.replace(/\\D/g, ''), 10) || 2090;
                }
                if (!finalImg) {
                    const iEl = card.querySelector('.home-wine-bottle-img');
                    if (iEl) finalImg = iEl.src;
                }
                if (!finalMeta) {
                    const mEl = card.querySelector('.home-wine-meta');
                    if (mEl) finalMeta = mEl.textContent.trim();
                }
            }

            // 2. Поиск в массивах популярных вин
            if (!finalTitle || !finalPrice) {
                const pool = (window.HOME_POPULAR_ROW_1 || []).concat(window.HOME_POPULAR_ROW_2 || []);
                const found = pool.find(w => w.slug === slug);
                if (found) {
                    finalTitle = finalTitle || found.title;
                    finalPrice = finalPrice || (typeof found.price === 'number' ? found.price : parseInt(String(found.price).replace(/\\D/g, ''), 10) || 2090);
                    finalMeta = finalMeta || found.meta;
                }
            }"""

new_code_html = """        function addWineToCartDirectly(slug, titleOrBtn, price, img, meta) {
            if (!slug) return;

            let clickedBtn = null;
            let finalTitle = '';
            let finalPrice = 0;
            let finalImg = '';
            let finalMeta = '';

            if (titleOrBtn && typeof titleOrBtn === 'object' && titleOrBtn.nodeType) {
                clickedBtn = titleOrBtn;
            } else if (typeof titleOrBtn === 'string') {
                finalTitle = titleOrBtn;
                finalPrice = typeof price === 'number' ? price : (parseInt(String(price).replace(/\\D/g, ''), 10) || 0);
                finalImg = img || '';
                finalMeta = meta || '';
            }

            if (!clickedBtn) {
                clickedBtn = (window.event && window.event.currentTarget) ? window.event.currentTarget : (window.event ? window.event.target : null);
            }

            let card = clickedBtn ? clickedBtn.closest('.home-wine-card, .catalog-wine-card-2col, [data-slug]') : null;
            if (!card && slug) {
                card = document.querySelector('[data-slug=\"' + slug + '\"]') || document.querySelector('.home-wine-card [onclick*=\"' + slug + '\"]')?.closest('.home-wine-card, .catalog-wine-card-2col');
            }

            if (card) {
                if (!finalTitle) {
                    const tEl = card.querySelector('.home-wine-title');
                    if (tEl) finalTitle = tEl.textContent.trim();
                }
                if (!finalPrice) {
                    const pEl = card.querySelector('.home-wine-price');
                    if (pEl) finalPrice = parseInt(pEl.textContent.replace(/\\D/g, ''), 10) || 2090;
                }
                if (!finalImg) {
                    const iEl = card.querySelector('.home-wine-bottle-img');
                    if (iEl) finalImg = iEl.src;
                }
                if (!finalMeta) {
                    const mEl = card.querySelector('.home-wine-meta');
                    if (mEl) finalMeta = mEl.textContent.trim();
                }
            }

            // Поиск в кэше каталога
            if ((!finalTitle || !finalPrice) && Array.isArray(window.CURRENT_CATALOG_ITEMS)) {
                const foundCat = window.CURRENT_CATALOG_ITEMS.find(w => w.slug === slug);
                if (foundCat) {
                    finalTitle = finalTitle || foundCat.name;
                    finalPrice = finalPrice || foundCat.price || 2090;
                    finalMeta = finalMeta || [foundCat.region, foundCat.color, '0.75 л'].filter(Boolean).join(', ');
                }
            }

            // Поиск в массивах популярных вин
            if (!finalTitle || !finalPrice) {
                const pool = (window.HOME_POPULAR_ROW_1 || []).concat(window.HOME_POPULAR_ROW_2 || []);
                const found = pool.find(w => w.slug === slug);
                if (found) {
                    finalTitle = finalTitle || found.title;
                    finalPrice = finalPrice || (typeof found.price === 'number' ? found.price : parseInt(String(found.price).replace(/\\D/g, ''), 10) || 2090);
                    finalMeta = finalMeta || found.meta;
                }
            }"""

if old_code_html in html:
    html = html.replace(old_code_html, new_code_html, 1)
    with open('static/scanner.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Updated scanner.html successfully!")
else:
    print("old_code_html not found in scanner.html")

# 2. Update CURRENT_CATALOG_ITEMS caching in fetchCatalogWines
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_cat_fetch = """                const items = data.items || [];
                const totalCount = data.count || items.length;

                stats.textContent = `Показано ${Math.min(catalogPageOffset + items.length, totalCount)} из ${totalCount} вин`;"""

new_cat_fetch = """                const items = data.items || [];
                const totalCount = data.count || items.length;
                window.CURRENT_CATALOG_ITEMS = (window.CURRENT_CATALOG_ITEMS || []).concat(items);

                stats.textContent = `Показано ${Math.min(catalogPageOffset + items.length, totalCount)} из ${totalCount} вин`;"""

if old_cat_fetch in html:
    html = html.replace(old_cat_fetch, new_cat_fetch, 1)
    with open('static/scanner.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Updated CURRENT_CATALOG_ITEMS caching in scanner.html!")
else:
    print("old_cat_fetch not found in scanner.html")

# 3. Update scanner.js
with open('static/scanner.js', 'r', encoding='utf-8') as f:
    js = f.read()

old_js = """    window.addWineToCartDirectly = function(slug, title, price, img, meta) {
        if (!slug) return;

        let finalTitle = title;
        let finalPrice = typeof price === 'number' ? price : (parseInt(String(price).replace(/\\D/g, ''), 10) || 0);
        let finalImg = img;
        let finalMeta = meta;

        const clickedBtn = (window.event && window.event.currentTarget) ? window.event.currentTarget : (window.event ? window.event.target : null);
        const card = clickedBtn ? clickedBtn.closest('.home-wine-card, .catalog-wine-card-2col, [data-slug]') : null;

        if (card) {
            if (!finalTitle) {
                const tEl = card.querySelector('.home-wine-title');
                if (tEl) finalTitle = tEl.textContent.trim();
            }
            if (!finalPrice) {
                const pEl = card.querySelector('.home-wine-price');
                if (pEl) finalPrice = parseInt(pEl.textContent.replace(/\\D/g, ''), 10) || 2090;
            }
            if (!finalImg) {
                const iEl = card.querySelector('.home-wine-bottle-img');
                if (iEl) finalImg = iEl.src;
            }
            if (!finalMeta) {
                const mEl = card.querySelector('.home-wine-meta');
                if (mEl) finalMeta = mEl.textContent.trim();
            }
        }

        if (!finalTitle || !finalPrice) {
            const pool = (window.HOME_POPULAR_ROW_1 || []).concat(window.HOME_POPULAR_ROW_2 || []);
            const found = pool.find(w => w.slug === slug);
            if (found) {
                finalTitle = finalTitle || found.title;
                finalPrice = finalPrice || (typeof found.price === 'number' ? found.price : parseInt(String(found.price).replace(/\\D/g, ''), 10) || 2090);
                finalMeta = finalMeta || found.meta;
            }
        }"""

new_js = """    window.addWineToCartDirectly = function(slug, titleOrBtn, price, img, meta) {
        if (!slug) return;

        let clickedBtn = null;
        let finalTitle = '';
        let finalPrice = 0;
        let finalImg = '';
        let finalMeta = '';

        if (titleOrBtn && typeof titleOrBtn === 'object' && titleOrBtn.nodeType) {
            clickedBtn = titleOrBtn;
        } else if (typeof titleOrBtn === 'string') {
            finalTitle = titleOrBtn;
            finalPrice = typeof price === 'number' ? price : (parseInt(String(price).replace(/\\D/g, ''), 10) || 0);
            finalImg = img || '';
            finalMeta = meta || '';
        }

        if (!clickedBtn) {
            clickedBtn = (window.event && window.event.currentTarget) ? window.event.currentTarget : (window.event ? window.event.target : null);
        }

        let card = clickedBtn ? clickedBtn.closest('.home-wine-card, .catalog-wine-card-2col, [data-slug]') : null;
        if (!card && slug) {
            card = document.querySelector('[data-slug=\"' + slug + '\"]') || document.querySelector('.home-wine-card [onclick*=\"' + slug + '\"]')?.closest('.home-wine-card, .catalog-wine-card-2col');
        }

        if (card) {
            if (!finalTitle) {
                const tEl = card.querySelector('.home-wine-title');
                if (tEl) finalTitle = tEl.textContent.trim();
            }
            if (!finalPrice) {
                const pEl = card.querySelector('.home-wine-price');
                if (pEl) finalPrice = parseInt(pEl.textContent.replace(/\\D/g, ''), 10) || 2090;
            }
            if (!finalImg) {
                const iEl = card.querySelector('.home-wine-bottle-img');
                if (iEl) finalImg = iEl.src;
            }
            if (!finalMeta) {
                const mEl = card.querySelector('.home-wine-meta');
                if (mEl) finalMeta = mEl.textContent.trim();
            }
        }

        if ((!finalTitle || !finalPrice) && Array.isArray(window.CURRENT_CATALOG_ITEMS)) {
            const foundCat = window.CURRENT_CATALOG_ITEMS.find(w => w.slug === slug);
            if (foundCat) {
                finalTitle = finalTitle || foundCat.name;
                finalPrice = finalPrice || foundCat.price || 2090;
                finalMeta = finalMeta || [foundCat.region, foundCat.color, '0.75 л'].filter(Boolean).join(', ');
            }
        }

        if (!finalTitle || !finalPrice) {
            const pool = (window.HOME_POPULAR_ROW_1 || []).concat(window.HOME_POPULAR_ROW_2 || []);
            const found = pool.find(w => w.slug === slug);
            if (found) {
                finalTitle = finalTitle || found.title;
                finalPrice = finalPrice || (typeof found.price === 'number' ? found.price : parseInt(String(found.price).replace(/\\D/g, ''), 10) || 2090);
                finalMeta = finalMeta || found.meta;
            }
        }"""

if old_js in js:
    js = js.replace(old_js, new_js, 1)
    with open('static/scanner.js', 'w', encoding='utf-8') as f:
        f.write(js)
    print("Updated scanner.js successfully!")
else:
    print("old_js not found in scanner.js")
