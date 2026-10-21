with open('static/scanner.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Ensure window.addWineToCartDirectly is defined
add_cart_directly_code = '''
    window.addWineToCartDirectly = function(slug, title, price, img, meta) {
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
    };

    window.deleteCartItem = function(slug) {
        let cart = window.getCartItems();
        cart = cart.filter(it => it.slug !== slug);
        window.saveCartItems(cart);
        window.renderCartPanel();
        if (typeof window.updateCartBadge === 'function') window.updateCartBadge();
        if (typeof showToast === 'function') showToast('Товар удален из корзины');
    };

    window.deleteSelectedCartItems = function() {
        let cart = window.getCartItems();
        const beforeCount = cart.length;
        cart = cart.filter(it => it.checked === false);
        if (cart.length === beforeCount) {
            if (typeof showToast === 'function') showToast('Нет выделенных товаров для удаления');
            return;
        }
        window.saveCartItems(cart);
        window.renderCartPanel();
        if (typeof window.updateCartBadge === 'function') window.updateCartBadge();
        if (typeof showToast === 'function') showToast('Выделенные товары удалены');
    };

    window.toggleCartSelectAll = function() {
        let cart = window.getCartItems();
        const allChecked = cart.every(it => it.checked !== false);
        const newChecked = !allChecked;
        cart.forEach(it => it.checked = newChecked);
        window.saveCartItems(cart);
        window.renderCartPanel();
    };
'''

# 2. Update renderCartPanel to include toolbar (Select All / Delete Selected) and single item delete
old_render_cart = '''        // 1. Рендеринг карточек вин
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
        }).join('');'''

new_render_cart = '''        // 1. Тулбар выделения и удаления
        const allChecked = cart.length > 0 && cart.every(w => w.checked !== false);
        const checkedCount = cart.filter(w => w.checked !== false).length;

        const toolbarHtml = `
            <div class="cart-action-toolbar">
                <button type="button" class="cart-select-all-btn" onclick="toggleCartSelectAll()">
                    <div class="cart-custom-checkbox ${allChecked ? 'checked' : ''}" style="width: 20px; height: 20px; border-radius: 6px;">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="3"><polyline points="20 6 9 17 4 12"></polyline></svg>
                    </div>
                    <span>Выбрать все</span>
                </button>
                <button type="button" class="btn-cart-delete-selected" onclick="deleteSelectedCartItems()">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    <span>Удалить выбранные (${checkedCount})</span>
                </button>
            </div>
        `;

        // 2. Рендеринг карточек вин с кнопкой удаления каждой позиции
        const cardsHtml = cart.map(w => {
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
                    <!-- В правом верхнем углу кнопка удаления одной позиции -->
                    <button type="button" class="cart-item-delete-btn" onclick="deleteCartItem('${w.slug}')" title="Удалить вино из корзины">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                    </button>
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

        container.innerHTML = toolbarHtml + cardsHtml;'''

if 'window.addWineToCartDirectly' not in js:
    js = js.replace('window.addCurrentDetailWineToCart = function', add_cart_directly_code + '\n    window.addCurrentDetailWineToCart = function')

if old_render_cart in js:
    js = js.replace(old_render_cart, new_render_cart)
else:
    print('Warning: old_render_cart exact match not found, checking normalized whitespace')

with open('static/scanner.js', 'w', encoding='utf-8') as f:
    f.write(js)
print('Updated static/scanner.js')
