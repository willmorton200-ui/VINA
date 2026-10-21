with open('static/scanner.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("previewStep === 'cart_click_test'", "previewStep === 'cart_click_test' || previewStep === 'cart_btn_feedback_test'", 1)

old_block = """            } else if (pStep === 'cart_click_test') {
                try { localStorage.removeItem('vina_cart'); } catch(e) {}
                switchHubTab('home');
                setTimeout(function() {
                    var btn = document.querySelector('.home-wine-card .btn-card-add-cart');
                    if (btn) btn.click();
                    setTimeout(function() {
                        switchHubTab('cart');
                    }, 400);
                }, 350);"""

new_block = """            } else if (pStep === 'cart_btn_feedback_test') {
                try { localStorage.removeItem('vina_cart'); } catch(e) {}
                switchHubTab('home');
                setTimeout(function() {
                    var btn = document.querySelector('.home-wine-card .btn-card-add-cart');
                    if (btn) btn.click();
                }, 400);
            } else if (pStep === 'cart_click_test') {
                try { localStorage.removeItem('vina_cart'); } catch(e) {}
                switchHubTab('home');
                setTimeout(function() {
                    var btn = document.querySelector('.home-wine-card .btn-card-add-cart');
                    if (btn) btn.click();
                    setTimeout(function() {
                        switchHubTab('cart');
                    }, 400);
                }, 350);"""

assert old_block in content, "old_block not found"
content = content.replace(old_block, new_block, 1)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("cart_btn_feedback_test added successfully!")
