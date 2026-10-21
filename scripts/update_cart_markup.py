import re

# 1. Update static/scanner.html
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the old hub-panel-cart
old_cart_panel = '''        <div id="hub-panel-cart" class="hub-panel">
            <div class="home-page-wrap" style="padding-bottom: 90px;">
                <h2 class="home-section-title" style="margin-bottom: 14px;">Корзина</h2>
                <div id="cart-items-box" class="hub-card" style="text-align: center; padding: 36px 20px;">
                    <p style="color: #6c757d; font-size: 15px; margin: 0 0 14px 0;">В корзине пока нет выбранных вин</p>
                    <button type="button" class="btn btn-primary" onclick="switchHubTab('catalog')" style="max-width: 220px; margin: 0 auto; border-radius: 10px; padding: 11px 18px;">Перейти в каталог</button>
                </div>
            </div>
        </div>'''

new_cart_panel = '''        <div id="hub-panel-cart" class="hub-panel">
            <div class="home-page-wrap" style="padding-bottom: 120px;">
                <div class="cart-header-row">
                    <h2 class="home-section-title">Корзина</h2>
                    <button type="button" id="cart-clear-btn" class="cart-clear-btn" onclick="clearEntireCart()" style="display: none;">Очистить всё</button>
                </div>
                
                <!-- Список карточек вин в корзине -->
                <div id="cart-items-container" class="cart-items-container">
                    <!-- Заполняется динамически через renderCartPanel() -->
                </div>

                <!-- Блок способов доставки (самовывоз / курьер) -->
                <div id="cart-delivery-section" class="cart-delivery-section" style="display: none;">
                    <h3 class="cart-section-subtitle">Способ получения</h3>
                    <div class="cart-delivery-options">
                        <!-- Вариант 1: Самовывоз -->
                        <div class="cart-delivery-card active" id="delivery-opt-pickup" onclick="setCartDeliveryMethod('pickup')">
                            <div class="cart-custom-checkbox checked" id="chk-delivery-pickup">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            </div>
                            <div class="cart-delivery-info">
                                <div class="cart-delivery-title">Самовывоз из винотеки</div>
                                <div class="cart-delivery-desc">Бесплатно · готовность от 15 минут в удобной винотеке</div>
                            </div>
                            <div class="cart-delivery-badge">0 ₽</div>
                        </div>

                        <!-- Вариант 2: Курьер -->
                        <div class="cart-delivery-card" id="delivery-opt-courier" onclick="setCartDeliveryMethod('courier')">
                            <div class="cart-custom-checkbox" id="chk-delivery-courier">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                                    <polyline points="20 6 9 17 4 12"></polyline>
                                </svg>
                            </div>
                            <div class="cart-delivery-info">
                                <div class="cart-delivery-title">Доставка курьером</div>
                                <div class="cart-delivery-desc">Экспресс к вашему столу · от 45 минут</div>
                            </div>
                            <div class="cart-delivery-badge" id="courier-price-badge">350 ₽</div>
                        </div>
                    </div>
                </div>

                <!-- Блок Итого и бордовая кнопка «Купить» -->
                <div id="cart-summary-section" class="cart-summary-section" style="display: none;">
                    <div class="cart-summary-rows">
                        <div class="cart-summary-line">
                            <span class="cart-sum-label">Выбрано товаров:</span>
                            <span class="cart-sum-val" id="cart-sum-count">0 шт.</span>
                        </div>
                        <div class="cart-summary-line">
                            <span class="cart-sum-label">Стоимость вин:</span>
                            <span class="cart-sum-val" id="cart-sum-items-total">0 ₽</span>
                        </div>
                        <div class="cart-summary-line">
                            <span class="cart-sum-label">Доставка:</span>
                            <span class="cart-sum-val" id="cart-sum-delivery">Бесплатно</span>
                        </div>
                        <div class="cart-summary-line total-line">
                            <span class="cart-total-label">Итого к оплате:</span>
                            <span class="cart-total-val" id="cart-sum-grand-total">0 ₽</span>
                        </div>
                    </div>
                    
                    <button type="button" class="btn-cart-buy" id="btn-cart-buy" onclick="handleCartCheckout()">
                        Купить
                    </button>
                </div>
            </div>
        </div>'''

if old_cart_panel in html:
    html = html.replace(old_cart_panel, new_cart_panel, 1)
    print('Replaced hub-panel-cart')
else:
    print('WARNING: old_cart_panel not found exactly, attempting normalized replace')
    old_norm = re.sub(r'\s+', ' ', old_cart_panel)
    pattern = re.compile(re.escape(old_cart_panel.strip()).replace(r'\ ', r'\s+'), re.DOTALL)
    if pattern.search(html):
        html = pattern.sub(new_cart_panel, html, 1)
        print('Replaced hub-panel-cart using regex')

# Add modal before </body>
modal_html = '''
    <!-- МОДАЛЬНОЕ ОКНО ОФОРМЛЕНИЯ ЗАКАЗА / КУПИТЬ -->
    <div id="cart-checkout-modal" class="cart-checkout-modal-overlay" onclick="if(event.target===this) closeCartCheckoutModal()">
        <div class="cart-checkout-modal-card">
            <div class="checkout-success-icon">
                <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
            </div>
            <div class="checkout-order-badge" id="checkout-order-num">Заказ № VN-84192</div>
            <h3 style="font-size: 20px; font-weight: 700; color: #1a1a1a; margin-bottom: 8px;">Заказ успешно оформлен!</h3>
            <p style="font-size: 14px; color: #495057; line-height: 1.45; margin-bottom: 16px;" id="checkout-order-desc">
                Спасибо за заказ в «Свое вино»! Мы уже начали собирать ваши выбранные вина.
            </p>
            <div style="background: #f8f9fa; border-radius: 12px; padding: 12px 14px; font-size: 13px; text-align: left; margin-bottom: 20px; border: 1px solid #eef0f3;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #6c757d;">Способ получения:</span>
                    <strong style="color: #1a1a1a;" id="checkout-modal-delivery">Самовывоз</strong>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #6c757d;">Количество вин:</span>
                    <strong style="color: #1a1a1a;" id="checkout-modal-qty">1 шт.</strong>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 14px; font-weight: 700; border-top: 1px dashed #dee2e6; padding-top: 6px;">
                    <span style="color: #1a1a1a;">Сумма заказа:</span>
                    <strong style="color: var(--primary);" id="checkout-modal-total">2 090 ₽</strong>
                </div>
            </div>
            <button type="button" class="btn btn-primary" onclick="closeCartCheckoutModal()" style="width: 100%; border-radius: 12px; padding: 13px; font-weight: 700;">
                Отлично! Вернуться в каталог
            </button>
        </div>
    </div>
'''

if 'id="cart-checkout-modal"' not in html:
    html = html.replace('</body>', modal_html + '\n</body>', 1)
    print('Added cart-checkout-modal')

with open('static/scanner.html', 'w', encoding='utf-8', newline='') as f:
    f.write(html)
print('scanner.html markup updated')
