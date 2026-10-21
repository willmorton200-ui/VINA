with open('d:/VINA/static/scanner.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("previewStep === 'catalog' ||", "previewStep === 'catalog' || previewStep === 'cart_click_test' ||", 1)

old_step = "} else if (pStep === 'cart') {"
new_step = """} else if (pStep === 'cart_click_test') {
                localStorage.removeItem('vina_cart');
                switchHubTab('catalog');
                setTimeout(function() {
                    var btn = document.querySelector('#catalog-wines-grid .btn-card-add-cart');
                    if (btn) {
                        btn.click();
                        setTimeout(function() {
                            switchHubTab('cart');
                        }, 800);
                    }
                }, 1200);
            } else if (pStep === 'cart') {"""

text = text.replace(old_step, new_step, 1)

with open('d:/VINA/static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Added cart_click_test preview step')
