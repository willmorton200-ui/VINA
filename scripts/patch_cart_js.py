import re

# Patch static/scanner.js
with open('static/scanner.js', 'r', encoding='utf-8') as f:
    js = f.read()

cart_functions_js = '''
    // =========================================================================
    // 6. УПРАВЛЕНИЕ КОРЗИНОЙ И ОФОРМЛЕНИЕ ЗАКАЗА
    // =========================================================================
    window.getCartItems = function() {
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
            checked: item.checked !== false, // по умолчанию галочки стоят
            img: item.img || '',
            meta: item.meta || 'Российское вино · 0.75 л'
        }));
    };

    window.saveCartItems = function(items) {
        try {
            localStorage.setItem('vina_cart', JSON.stringify(items));
        } catch(e) { console.warn(e); }
        window.updateCartBadge();
    };

    window.updateCartBadge = function() {
        let count = 0;
        try {
            const cart = window.getCartItems();
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
    };

    window.ensureSampleCartItem = function() {
        let cart = window.getCartItems();
        if (cart.length === 0) {
            cart = [{
                slug: 'loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131',
                title: 'Loco Cimbali Blanc de Neige',
                winery: 'Loco Cimbali',
                price: 2090,
                qty: 1,
                checked: true,
                img: '../wines_images_clean/wines_images/loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131.webp',
                meta: 'Крым · Белое, сухое · 0.75 л'
            }];
            window.saveCartItems(cart);
        }
    };

    window.addCurrentDetailWineToCart = function(customSlug, customWine) {
        let cart = window.getCartItems();
        const slug = customSlug || window.currentDetailWineSlug || 'loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131';
        const existing = cart.find(item => item.slug === slug);

        if (existing) {
            existing.qty = (existing.qty || 1) + 1;
            existing.checked = true;
        } else {
            let title = 'Вино';
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
                if (titleEl && titleEl.textContent) title = titleEl.textContent;

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

        window.saveCartItems(cart);

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
            showToast('✓ Товар добавлен в корзину');
        }

        const cartPanel = document.getElementById('hub-panel-cart');
        if (cartPanel && cartPanel.classList.contains('active')) {
            window.renderCartPanel();
        }
    };

    window.toggleCartItemChecked = function(slug) {
        const cart = window.getCartItems();
        const item = cart.find(it => it.slug === slug);
        if (item) {
            item.checked = !item.checked;
            window.saveCartItems(cart);
            window.renderCartPanel();
        }
    };

    window.changeCartItemQty = function(slug, delta) {
        let cart = window.getCartItems();
        const item = cart.find(it => it.slug === slug);
        if (item) {
            item.qty = (item.qty || 1) + delta;
            if (item.qty <= 0) {
                cart = cart.filter(it => it.slug !== slug);
            }
            window.saveCartItems(cart);
            window.renderCartPanel();
        }
    };

    window.removeCartItem = function(slug) {
        let cart = window.getCartItems();
        cart = cart.filter(it => it.slug !== slug);
        window.saveCartItems(cart);
        window.renderCartPanel();
    };

    window.clearEntireCart = function() {
        window.saveCartItems([]);
        window.renderCartPanel();
        if (typeof showToast === 'function') {
            showToast('Корзина очищена');
        }
    };

    window.setCartDeliveryMethod = function(method) {
        try {
            localStorage.setItem('vina_cart_delivery', method);
        } catch(e) {}
        window.renderCartPanel();
    };

    window.renderCartPanel = function() {
        const container = document.getElementById('cart-items-container');
        const deliverySec = document.getElementById('cart-delivery-section');
        const summarySec = document.getElementById('cart-summary-section');
        const clearBtn = document.getElementById('cart-clear-btn');
        if (!container) return;

        const cart = window.getCartItems();

        if (cart.length === 0) {
            if (clearBtn) clearBtn.style.display = 'none';
            if (deliverySec) deliverySec.style.display = 'none';
            if (summarySec) summarySec.style.display = 'none';

            container.innerHTML = `
                <div class="cart-empty-box">
                    <div class="cart-empty-icon-wrap">
                        <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="var(--primary, #800020)" stroke-width="2">
                            <path d="M5 7h14l-1 13H6L5 7z"></path>
                            <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                        </svg>
                    </div>
                    <div class="cart-empty-title">В вашей корзине пока пусто</div>
                    <div class="cart-empty-desc">
                        Выберите понравившиеся российские вина в каталоге или сканере и добавьте их в корзину.
                    </div>
                    <button type="button" class="btn btn-primary" onclick="switchHubTab('catalog')" style="border-radius: 12px; padding: 12px 24px; font-weight: 700;">
                        Перейти в каталог
                    </button>
                </div>
            `;
            return;
        }

        if (clearBtn) clearBtn.style.display = 'inline-block';
        if (deliverySec) deliverySec.style.display = 'block';
        if (summarySec) summarySec.style.display = 'block';

        // 1. Рендеринг карточек вин
        container.innerHTML = cart.map(w => {
            const isChecked = w.checked !== false;
            const price = w.price || 2090;
            const qty = w.qty || 1;
            const itemTotal = price * qty;
            const localImg = `../wines_images_clean/wines_images/${w.slug}.webp`;
            const apiImg = `${getHubApiBase()}/api/image/${w.slug}`;
            const imgSrc = w.img || ((window.location.protocol === 'file:') ? localImg : apiImg);

            return `
                <div class="cart-wine-card ${isChecked ? 'checked-card' : ''}" data-slug="${w.slug}">
                    <!-- В углу карточки вверху слева квадратик с галочкой (по умолчанию стоят) -->
                    <div class="cart-wine-card-checkbox">
                        <div class="cart-custom-checkbox ${isChecked ? 'checked' : ''}" onclick="toggleCartItemChecked('${w.slug}')" title="Выбрать для покупки">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                    </div>
                    <div class="cart-wine-thumb-box" onclick="openWineDetail('${w.slug}')">
                        <img src="${imgSrc}" class="cart-wine-thumb-img" alt="${w.title}" onerror="this.src='badge_glass.png'">
                    </div>
                    <div class="cart-wine-info">
                        <h4 class="cart-wine-title" onclick="openWineDetail('${w.slug}')" title="${w.title}">${w.title}</h4>
                        <div class="cart-wine-meta">${w.meta || 'Российское вино · 0.75 л'}</div>
                        <div class="cart-wine-unit-price">${price.toLocaleString('ru-RU')} ₽ / шт</div>
                    </div>
                    <!-- Справа - количество шт, в стиле бордово-сером -->
                    <div class="cart-wine-right-col">
                        <div class="cart-qty-control">
                            <button type="button" class="cart-qty-btn minus" onclick="changeCartItemQty('${w.slug}', -1)" title="Уменьшить">-</button>
                            <span class="cart-qty-val">${qty} шт</span>
                            <button type="button" class="cart-qty-btn plus" onclick="changeCartItemQty('${w.slug}', 1)" title="Увеличить">+</button>
                        </div>
                        <div class="cart-item-total-price">${itemTotal.toLocaleString('ru-RU')} ₽</div>
                    </div>
                </div>
            `;
        }).join('');

        // 2. Способ получения (самовывоз / курьер)
        const deliveryMethod = localStorage.getItem('vina_cart_delivery') || 'pickup';
        const cardPickup = document.getElementById('delivery-opt-pickup');
        const cardCourier = document.getElementById('delivery-opt-courier');
        const chkPickup = document.getElementById('chk-delivery-pickup');
        const chkCourier = document.getElementById('chk-delivery-courier');

        if (cardPickup && cardCourier && chkPickup && chkCourier) {
            const isPickup = deliveryMethod === 'pickup';
            cardPickup.classList.toggle('active', isPickup);
            chkPickup.classList.toggle('checked', isPickup);
            cardCourier.classList.toggle('active', !isPickup);
            chkCourier.classList.toggle('checked', !isPickup);
        }

        // 3. Подсчет итоговых сумм
        const checkedItems = cart.filter(w => w.checked !== false);
        const checkedCount = checkedItems.reduce((acc, it) => acc + (it.qty || 1), 0);
        const itemsTotal = checkedItems.reduce((acc, it) => acc + ((it.price || 0) * (it.qty || 1)), 0);

        let deliveryFee = 0;
        let deliveryLabel = 'Бесплатно (Самовывоз)';

        if (deliveryMethod === 'courier') {
            if (itemsTotal >= 5000 || checkedCount === 0) {
                deliveryFee = 0;
                deliveryLabel = 'Бесплатно (от 5 000 ₽)';
            } else {
                deliveryFee = 350;
                deliveryLabel = '350 ₽ (Курьер)';
            }
        }

        const grandTotal = checkedCount > 0 ? (itemsTotal + deliveryFee) : 0;

        const countEl = document.getElementById('cart-sum-count');
        if (countEl) countEl.textContent = `${checkedCount} шт.`;

        const totalItemsEl = document.getElementById('cart-sum-items-total');
        if (totalItemsEl) totalItemsEl.textContent = `${itemsTotal.toLocaleString('ru-RU')} ₽`;

        const delivEl = document.getElementById('cart-sum-delivery');
        if (delivEl) delivEl.textContent = deliveryLabel;

        const grandEl = document.getElementById('cart-sum-grand-total');
        if (grandEl) grandEl.textContent = `${grandTotal.toLocaleString('ru-RU')} ₽`;

        // 4. Бордовая кнопка «Купить»
        const buyBtn = document.getElementById('btn-cart-buy');
        if (buyBtn) {
            if (checkedCount > 0) {
                buyBtn.disabled = false;
                buyBtn.textContent = `Купить · ${grandTotal.toLocaleString('ru-RU')} ₽`;
            } else {
                buyBtn.disabled = true;
                buyBtn.textContent = 'Выберите вина для покупки';
            }
        }
    };

    window.handleCartCheckout = function() {
        const cart = window.getCartItems();
        const checkedItems = cart.filter(w => w.checked !== false);
        if (checkedItems.length === 0) {
            if (typeof showToast === 'function') showToast('Выберите хотя бы одно вино для покупки');
            return;
        }

        const deliveryMethod = localStorage.getItem('vina_cart_delivery') || 'pickup';
        const checkedCount = checkedItems.reduce((acc, it) => acc + (it.qty || 1), 0);
        const itemsTotal = checkedItems.reduce((acc, it) => acc + ((it.price || 0) * (it.qty || 1)), 0);
        const deliveryFee = (deliveryMethod === 'courier' && itemsTotal < 5000) ? 350 : 0;
        const grandTotal = itemsTotal + deliveryFee;

        const randNum = Math.floor(10000 + Math.random() * 90000);
        const orderNum = `VN-${randNum}`;

        const modal = document.getElementById('cart-checkout-modal');
        const numEl = document.getElementById('checkout-order-num');
        const delivEl = document.getElementById('checkout-modal-delivery');
        const qtyEl = document.getElementById('checkout-modal-qty');
        const totalEl = document.getElementById('checkout-modal-total');

        if (numEl) numEl.textContent = `Заказ № ${orderNum}`;
        if (delivEl) delivEl.textContent = deliveryMethod === 'courier' ? 'Доставка курьером' : 'Самовывоз из винотеки';
        if (qtyEl) qtyEl.textContent = `${checkedCount} шт.`;
        if (totalEl) totalEl.textContent = `${grandTotal.toLocaleString('ru-RU')} ₽`;

        if (modal) modal.classList.add('visible');

        const remaining = cart.filter(w => w.checked === false);
        window.saveCartItems(remaining);
    };

    window.closeCartCheckoutModal = function() {
        const modal = document.getElementById('cart-checkout-modal');
        if (modal) modal.classList.remove('visible');
        window.renderCartPanel();
        if (typeof switchHubTab === 'function') {
            switchHubTab('catalog');
        }
    };
'''

if 'window.renderCartPanel' not in js:
    # Append inside IIFE or before end
    # Find last closing of IIFE: })();
    if '})();' in js:
        js = js[:js.rfind('})();')] + cart_functions_js + '\n})();\n'
    else:
        js = js + '\n' + cart_functions_js
    with open('static/scanner.js', 'w', encoding='utf-8', newline='') as f:
        f.write(js)
    print('scanner.js updated with cart functions')
else:
    print('scanner.js already contains cart functions')

# Also update static/scanner.html to ensure switchHubTab('cart') calls renderCartPanel() and preview_step='cart' is handled
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Update switchHubTab
target_switch = '''                } else if (tabName === 'favorites') {
                    renderFavoritesPanel();'''

replacement_switch = '''                } else if (tabName === 'favorites') {
                    renderFavoritesPanel();
                } else if (tabName === 'cart') {
                    if (typeof window.renderCartPanel === 'function') {
                        window.renderCartPanel();
                    }'''

if target_switch in html and "tabName === 'cart'" not in html[html.find(target_switch):html.find(target_switch)+250]:
    html = html.replace(target_switch, replacement_switch, 1)
    print('Updated switchHubTab in scanner.html')

# Update DOMContentLoaded preview_step
target_preview = '''            } else if (pStep === 'toasts') {'''
replacement_preview = '''            } else if (pStep === 'cart') {
                if (typeof window.ensureSampleCartItem === 'function') window.ensureSampleCartItem();
                switchHubTab('cart');
            } else if (pStep === 'toasts') {'''

if target_preview in html and "pStep === 'cart'" not in html:
    html = html.replace(target_preview, replacement_preview, 1)
    print('Updated preview_step handling in scanner.html')

with open('static/scanner.html', 'w', encoding='utf-8', newline='') as f:
    f.write(html)
print('scanner.html updated with switchHubTab and preview_step')
