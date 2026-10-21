import re, os

# 1. Update static/scanner.css
with open('static/scanner.css', 'r', encoding='utf-8') as f:
    css = f.read()

cart_css = '''
/* ========================================================================== */
/* КОРЗИНА И ОФОРМЛЕНИЕ ЗАКАЗА                                                */
/* ========================================================================== */
.cart-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}
.cart-clear-btn {
    background: none;
    border: none;
    color: #868e96;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 6px;
    transition: all 0.15s ease;
}
.cart-clear-btn:hover {
    color: var(--primary, #800020);
    background: #fff0f3;
}

/* СТИЛЬНЫЙ ЧЕКБОКС ГАЛОЧКА / НЕТ */
.cart-custom-checkbox {
    width: 22px;
    height: 22px;
    border-radius: 6px;
    border: 2px solid #ced4da;
    background: #ffffff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    flex-shrink: 0;
}
.cart-custom-checkbox:hover {
    border-color: var(--primary, #800020);
}
.cart-custom-checkbox svg {
    opacity: 0;
    transform: scale(0.6);
    transition: all 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.cart-custom-checkbox.checked {
    background: var(--primary, #800020);
    border-color: var(--primary, #800020);
}
.cart-custom-checkbox.checked svg {
    opacity: 1;
    transform: scale(1);
    stroke: #ffffff;
}

/* КАРТОЧКА ВИНА В КОРЗИНЕ */
.cart-items-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
}
.cart-wine-card {
    position: relative;
    display: flex;
    align-items: center;
    background: #ffffff;
    border: 1px solid var(--border-color, #eef0f3);
    border-radius: 14px;
    padding: 14px 14px 14px 44px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    gap: 12px;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.cart-wine-card.checked-card {
    border-color: #ebd0d7;
}

/* 1. В углу карточки вверху слева квадратик с галочкой */
.cart-wine-card-checkbox {
    position: absolute;
    top: 12px;
    left: 12px;
    z-index: 2;
}

.cart-wine-thumb-box {
    width: 58px;
    height: 74px;
    background: #fbfbfc;
    border-radius: 10px;
    border: 1px solid #f1f3f5;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex-shrink: 0;
}
.cart-wine-thumb-img {
    max-height: 90%;
    max-width: 90%;
    object-fit: contain;
}

.cart-wine-info {
    flex: 1;
    min-width: 0;
}
.cart-wine-title {
    font-size: 14px;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 3px 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    cursor: pointer;
}
.cart-wine-meta {
    font-size: 12px;
    color: #6c757d;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cart-wine-unit-price {
    font-size: 13px;
    font-weight: 600;
    color: #495057;
}

/* Справа - количество шт, в стиле бордово-сером */
.cart-wine-right-col {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
    flex-shrink: 0;
}
.cart-qty-control {
    display: inline-flex;
    align-items: center;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    overflow: hidden;
}
.cart-qty-btn {
    width: 28px;
    height: 28px;
    background: transparent;
    border: none;
    color: #495057;
    font-size: 16px;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
}
.cart-qty-btn:hover {
    background: var(--primary, #800020);
    color: #ffffff;
}
.cart-qty-val {
    font-size: 13px;
    font-weight: 700;
    color: #1a1a1a;
    padding: 0 4px;
    min-width: 44px;
    text-align: center;
    user-select: none;
}
.cart-item-total-price {
    font-size: 14px;
    font-weight: 700;
    color: var(--primary, #800020);
}

/* БЛОК ДОСТАВКИ */
.cart-delivery-section {
    background: #ffffff;
    border: 1px solid var(--border-color, #eef0f3);
    border-radius: 14px;
    padding: 16px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.cart-section-subtitle {
    font-size: 15px;
    font-weight: 700;
    color: #1a1a1a;
    margin: 0 0 12px 0;
}
.cart-delivery-options {
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.cart-delivery-card {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 14px;
    border-radius: 10px;
    border: 1.5px solid #e9ecef;
    background: #fbfbfc;
    cursor: pointer;
    transition: all 0.2s ease;
}
.cart-delivery-card:hover {
    border-color: #d1b5bc;
    background: #fffafa;
}
.cart-delivery-card.active {
    border-color: var(--primary, #800020);
    background: #fff8f9;
}
.cart-delivery-info {
    flex: 1;
}
.cart-delivery-title {
    font-size: 14px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 2px;
}
.cart-delivery-desc {
    font-size: 12px;
    color: #6c757d;
}
.cart-delivery-badge {
    font-size: 13px;
    font-weight: 700;
    color: var(--primary, #800020);
    padding: 4px 8px;
    border-radius: 6px;
    background: rgba(128, 0, 32, 0.08);
}

/* ИТОГО И БОРДОВАЯ КНОПКА КУПИТЬ */
.cart-summary-section {
    background: #ffffff;
    border: 1px solid var(--border-color, #eef0f3);
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
}
.cart-summary-rows {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 16px;
}
.cart-summary-line {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 14px;
    color: #495057;
}
.cart-summary-line.total-line {
    border-top: 1px dashed #dee2e6;
    padding-top: 10px;
    margin-top: 4px;
    font-size: 16px;
    font-weight: 800;
    color: #1a1a1a;
}
.cart-total-val {
    color: var(--primary, #800020);
    font-size: 20px;
    font-weight: 800;
}
.btn-cart-buy {
    width: 100%;
    background: var(--primary, #800020);
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
    padding: 15px 20px;
    border-radius: 12px;
    border: none;
    cursor: pointer;
    box-shadow: 0 4px 14px rgba(128, 0, 32, 0.25);
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
}
.btn-cart-buy:hover {
    background: var(--primary-light, #a31c3b);
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(128, 0, 32, 0.35);
}
.btn-cart-buy:active {
    transform: translateY(0);
}
.btn-cart-buy:disabled {
    background: #ced4da;
    color: #6c757d;
    cursor: not-allowed;
    box-shadow: none;
    transform: none;
}

/* ПУСТАЯ КОРЗИНА */
.cart-empty-box {
    text-align: center;
    padding: 40px 20px;
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid var(--border-color, #eef0f3);
}
.cart-empty-icon-wrap {
    width: 68px;
    height: 68px;
    margin: 0 auto 16px auto;
    border-radius: 50%;
    background: #fdf2f4;
    display: flex;
    align-items: center;
    justify-content: center;
}
.cart-empty-title {
    font-size: 17px;
    font-weight: 700;
    color: #1a1a1a;
    margin-bottom: 8px;
}
.cart-empty-desc {
    font-size: 13px;
    color: #6c757d;
    max-width: 340px;
    margin: 0 auto 18px auto;
    line-height: 1.4;
}

/* МОДАЛЬНОЕ ОКНО УСПЕШНОГО ОФОРМЛЕНИЯ ЗАКАЗА */
.cart-checkout-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    padding: 20px;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.25s ease;
}
.cart-checkout-modal-overlay.visible {
    opacity: 1;
    pointer-events: auto;
}
.cart-checkout-modal-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 28px 24px;
    max-width: 420px;
    width: 100%;
    text-align: center;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.2);
    transform: translateY(20px);
    transition: transform 0.25s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.cart-checkout-modal-overlay.visible .cart-checkout-modal-card {
    transform: translateY(0);
}
.checkout-success-icon {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: #f0fdf4;
    border: 2px solid #bbf7d0;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 16px auto;
}
.checkout-order-badge {
    display: inline-block;
    padding: 5px 12px;
    border-radius: 8px;
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    font-size: 13px;
    font-weight: 700;
    color: var(--primary, #800020);
    margin-bottom: 12px;
}
'''

if '/* КОРЗИНА И ОФОРМЛЕНИЕ ЗАКАЗА' not in css:
    css = css + '\n' + cart_css
    with open('static/scanner.css', 'w', encoding='utf-8', newline='') as f:
        f.write(css)
    print('scanner.css updated with cart styles')
else:
    print('scanner.css already contains cart styles')
