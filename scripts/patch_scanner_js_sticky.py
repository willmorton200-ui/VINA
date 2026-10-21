with open('static/scanner.js', 'r', encoding='utf-8') as f:
    js = f.read()

target = """            const btnStickyCart = document.getElementById('btn-detail-sticky-cart');
            if (btnStickyCart) {
                btnStickyCart.onclick = () => {
                    if (typeof window.addCurrentDetailWineToCart === 'function') {
                        window.addCurrentDetailWineToCart();
                    }
                };
            }"""

replacement = """            const btnStickyMap = document.getElementById('btn-detail-sticky-map');
            if (btnStickyMap) {
                btnStickyMap.onclick = () => {
                    if (typeof window.findStoresForCurrentWine === 'function') {
                        window.findStoresForCurrentWine();
                    } else if (typeof window.switchHubTab === 'function') {
                        window.switchHubTab('map');
                    }
                };
            }"""

assert target in js, "target not found in scanner.js"
js = js.replace(target, replacement, 1)

with open('static/scanner.js', 'w', encoding='utf-8') as f:
    f.write(js)

print("Updated scanner.js successfully!")
