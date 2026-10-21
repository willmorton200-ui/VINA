# -*- coding: utf-8 -*-
import re

# 1. Read scanner.html
with open('d:/VINA/static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace script tag versions to bust cache
html = re.sub(r'scanner\.js\?v=\d+', 'scanner.js?v=34', html)
html = re.sub(r'scanner\.css\?v=\d+', 'scanner.css?v=39', html)

# Replace the broken stubs around line 3354
old_stubs = """        function addWineToCartDirectly(slug, title, price, img, meta) {
            if (typeof window.addWineToCartDirectly === 'function') {
                return window.addWineToCartDirectly(slug, title, price, img, meta);
            }
        }

        function addCurrentDetailWineToCart(customSlug, customWine) {
            if (typeof window.addCurrentDetailWineToCart === 'function') {
                return window.addCurrentDetailWineToCart(customSlug, customWine);
            }
        }"""

new_implementations = """        function getCartItems() {
            let cart = [];
            try {
                cart = JSON.parse(localStorage.getItem('vina_cart') || '[]');
            } catch(e) { cart = []; }
            if (!Array.isArray(cart)) cart = [];
            return cart.map(item => ({
                slug: item.slug || 'wine',
                title: item.title || 'Свое вино',
                winery: item.winery || '',
                price: typeof item.price === 'number' ? item.price : (parseInt(item.price, 10) || 2090),
                qty: typeof item.qty === 'number' && item.qty > 0 ? item.qty : 1,
                checked: item.checked !== false,
                img: item.img || '',
                meta: item.meta || 'Российское вино · 0.75 л'
            }));
        }
        window.getCartItems = getCartItems;

        function saveCartItems(items) {
            try {
                localStorage.setItem('vina_cart', JSON.stringify(items));
            } catch(e) { console.warn(e); }
            updateCartBadge();
        }
        window.saveCartItems = saveCartItems;

        function updateCartBadge() {
            let count = 0;
            try {
                const cart = JSON.parse(localStorage.getItem('vina_cart') || '[]');
                if (Array.isArray(cart)) {
                    count = cart.reduce((acc, it) => acc + (it.qty || 1), 0);
                }
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
        window.updateCartBadge = updateCartBadge;

        function addWineToCartDirectly(slug, title, price, img, meta) {
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
            }

            if (!finalTitle) finalTitle = 'Российское вино';
            if (!finalPrice) finalPrice = 2090;
            if (!finalImg) {
                const localImg = `../wines_images_clean/wines_images/${slug}.webp`;
                const apiImg = `${getHubApiBase()}/api/image/${slug}`;
                finalImg = (window.location.protocol === 'file:') ? localImg : apiImg;
            }
            if (!finalMeta) finalMeta = 'Россия · 0.75 л';

            let cart = getCartItems();
            const existing = cart.find(it => it.slug === slug);
            if (existing) {
                existing.qty = (existing.qty || 1) + 1;
                existing.checked = true;
            } else {
                cart.push({
                    slug: slug,
                    title: finalTitle,
                    price: finalPrice,
                    qty: 1,
                    checked: true,
                    img: finalImg,
                    meta: finalMeta
                });
            }

            saveCartItems(cart);

            // Визуальный отклик на кнопке
            if (clickedBtn) {
                const btn = clickedBtn.closest('.btn-card-add-cart') || clickedBtn;
                if (btn && btn.classList.contains('btn-card-add-cart')) {
                    const origHtml = btn.innerHTML;
                    btn.classList.add('added');
                    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> <span>В корзине!</span>';
                    setTimeout(() => {
                        btn.classList.remove('added');
                        btn.innerHTML = origHtml;
                    }, 1400);
                }
            }

            if (typeof showToast === 'function') {
                showToast(`✓ «${finalTitle}» добавлено в корзину`);
            }

            const cartPanel = document.getElementById('hub-panel-cart');
            if (cartPanel && cartPanel.classList.contains('active')) {
                if (typeof window.renderCartPanel === 'function') {
                    window.renderCartPanel();
                }
            }
        }
        window.addWineToCartDirectly = addWineToCartDirectly;

        function addCurrentDetailWineToCart(customSlug, customWine) {
            const slug = customSlug || window.currentDetailWineSlug || 'loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131';
            let title = 'Российское вино';
            let price = window.currentDetailWinePrice || 2090;
            let meta = 'Российское вино · 0.75 л';
            let img = '';

            if (customWine) {
                title = customWine.name || customWine.title || slug;
                price = customWine.price || 2090;
                meta = customWine.meta || `${customWine.region || 'Россия'} · ${customWine.color || ''}, ${customWine.sweetness || customWine.sugar || ''} · 0.75 л`;
                img = customWine.image_url || customWine.img || '';
            } else {
                const titleEl = document.getElementById('detail-wine-title');
                if (titleEl && titleEl.textContent && titleEl.textContent !== 'Загрузка карточки вина...') {
                    title = titleEl.textContent.trim();
                }
                const color = document.getElementById('detail-wine-color')?.textContent || '';
                const sugar = document.getElementById('detail-wine-sugar')?.textContent || '';
                const region = document.getElementById('detail-wine-region')?.textContent || '';
                meta = [region, color && sugar ? `${color}, ${sugar.toLowerCase()}` : (color || sugar), '0.75 л'].filter(Boolean).join(' · ');

                const imgEl = document.getElementById('detail-wine-img');
                if (imgEl && imgEl.src) img = imgEl.src;
            }

            if (!img) {
                const localImg = `../wines_images_clean/wines_images/${slug}.webp`;
                const apiImg = `${getHubApiBase()}/api/image/${slug}`;
                img = (window.location.protocol === 'file:') ? localImg : apiImg;
            }

            let cart = getCartItems();
            const existing = cart.find(item => item.slug === slug);
            if (existing) {
                existing.qty = (existing.qty || 1) + 1;
                existing.checked = true;
            } else {
                cart.push({
                    slug: slug,
                    title: title,
                    price: price,
                    qty: 1,
                    checked: true,
                    img: img,
                    meta: meta
                });
            }

            saveCartItems(cart);

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

            if (typeof showToast === 'function') {
                showToast(`✓ «${title}» добавлено в корзину`);
            }

            const cartPanel = document.getElementById('hub-panel-cart');
            if (cartPanel && cartPanel.classList.contains('active')) {
                if (typeof window.renderCartPanel === 'function') {
                    window.renderCartPanel();
                }
            }
        }
        window.addCurrentDetailWineToCart = addCurrentDetailWineToCart;"""

if old_stubs in html:
    html = html.replace(old_stubs, new_implementations, 1)
    print("Replaced recursive stubs in scanner.html successfully")
else:
    print("WARNING: old_stubs not found verbatim in scanner.html")

# Simplify onclick in renderHomeWineCard to addWineToCartDirectly('${w.slug}')
html = re.sub(
    r"""<button type="button" class="btn-card-add-cart" onclick="event\.stopPropagation\(\);\s*addWineToCartDirectly\([^)]+\)" title="Добавить в корзину">""",
    r"""<button type="button" class="btn-card-add-cart" onclick="event.stopPropagation(); addWineToCartDirectly('${w.slug}')" title="Добавить в корзину">""",
    html
)

with open('d:/VINA/static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Updated scanner.html")

# 2. Update scanner.js
with open('d:/VINA/static/scanner.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Replace addWineToCartDirectly in scanner.js with matching logic
old_js_add = """    window.addWineToCartDirectly = function(slug, title, price, img, meta) {
        if (!slug) return;
        let cart = window.getCartItems();
        const existing = cart.find(it => it.slug === slug);
        if (existing) {
            existing.qty = (existing.qty || 1) + 1;
            existing.checked = true;
        } else {
            const localImg = `../wines_images_clean/wines_images/${slug}.webp`;
            const apiImg = `${getHubApiBase()}/api/image/${slug}`;
            const finalImg = img || ((window.location.protocol === 'file:') ? localImg : apiImg);

            cart.push({
                slug: slug,
                title: title || 'Российское вино',
                price: Number(price) || 2090,
                qty: 1,
                checked: true,
                img: finalImg,
                meta: meta || 'Россия · 0.75 л'
            });
        }
        window.saveCartItems(cart);
        if (typeof window.updateCartBadge === 'function') window.updateCartBadge();

        if (window.event && window.event.currentTarget) {
            const btn = window.event.currentTarget;
            const origText = btn.innerHTML;
            btn.classList.add('added');
            btn.innerHTML = '<span>✓ В корзине</span>';
            setTimeout(() => {
                btn.classList.remove('added');
                btn.innerHTML = origText;
            }, 1400);
        }

        if (typeof showToast === 'function') {
            showToast(`✓ «${title || 'Вино'}» добавлено в корзину`);
        }

        const cartPanel = document.getElementById('hub-panel-cart');
        if (cartPanel && cartPanel.classList.contains('active')) {
            window.renderCartPanel();
        }
    };"""

new_js_add = """    window.addWineToCartDirectly = function(slug, title, price, img, meta) {
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
        }

        if (!finalTitle) finalTitle = 'Российское вино';
        if (!finalPrice) finalPrice = 2090;
        if (!finalImg) {
            const localImg = `../wines_images_clean/wines_images/${slug}.webp`;
            const apiImg = `${getHubApiBase()}/api/image/${slug}`;
            finalImg = (window.location.protocol === 'file:') ? localImg : apiImg;
        }
        if (!finalMeta) finalMeta = 'Россия · 0.75 л';

        let cart = window.getCartItems();
        const existing = cart.find(it => it.slug === slug);
        if (existing) {
            existing.qty = (existing.qty || 1) + 1;
            existing.checked = true;
        } else {
            cart.push({
                slug: slug,
                title: finalTitle,
                price: finalPrice,
                qty: 1,
                checked: true,
                img: finalImg,
                meta: finalMeta
            });
        }

        window.saveCartItems(cart);
        if (typeof window.updateCartBadge === 'function') window.updateCartBadge();

        if (clickedBtn) {
            const btn = clickedBtn.closest('.btn-card-add-cart') || clickedBtn;
            if (btn && btn.classList.contains('btn-card-add-cart')) {
                const origHtml = btn.innerHTML;
                btn.classList.add('added');
                btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> <span>В корзине!</span>';
                setTimeout(() => {
                    btn.classList.remove('added');
                    btn.innerHTML = origHtml;
                }, 1400);
            }
        }

        if (typeof showToast === 'function') {
            showToast(`✓ «${finalTitle}» добавлено в корзину`);
        }

        const cartPanel = document.getElementById('hub-panel-cart');
        if (cartPanel && cartPanel.classList.contains('active')) {
            window.renderCartPanel();
        }
    };"""

if old_js_add in js:
    js = js.replace(old_js_add, new_js_add, 1)
    print("Replaced addWineToCartDirectly in scanner.js successfully")
else:
    print("WARNING: old_js_add not found verbatim in scanner.js")

with open('d:/VINA/static/scanner.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("Updated scanner.js")
