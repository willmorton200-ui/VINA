import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'
p_multi = os.path.join(out_dir, 'preview_cart_multi.png')

# HTML script that seeds 2 items into localStorage, renders cart, and takes screenshot
html_multi_test = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="margin: 0; padding: 0;">
<iframe id="cart-frame" src="scanner.html?preview_step=cart" style="width: 480px; height: 932px; border: none;"></iframe>
<script>
window.onload = function() {
    setTimeout(function() {
        const frame = document.getElementById('cart-frame').contentWindow;
        const testCart = [
            {
                slug: 'loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131',
                title: 'Loco Cimbali Blanc de Neige',
                winery: 'Loco Cimbali',
                price: 2090,
                qty: 1,
                checked: true,
                img: '../wines_images_clean/wines_images/loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131.webp',
                meta: 'Крым · Белое, сухое · 0.75 л'
            },
            {
                slug: 'alma-valley-pinot-noir-krasnoe-suhoe',
                title: 'Alma Valley Pinot Noir',
                winery: 'Alma Valley',
                price: 1850,
                qty: 2,
                checked: true,
                img: 'badge_glass.png',
                meta: 'Крым · Красное, сухое · 0.75 л'
            }
        ];
        frame.localStorage.setItem('vina_cart', JSON.stringify(testCart));
        frame.localStorage.setItem('vina_cart_delivery', 'pickup');
        if (typeof frame.renderCartPanel === 'function') {
            frame.renderCartPanel();
        }
        if (typeof frame.updateCartBadge === 'function') {
            frame.updateCartBadge();
        }
    }, 400);
};
</script>
</body>
</html>
"""

with open('static/test_cart_multi.html', 'w', encoding='utf-8') as f:
    f.write(html_multi_test)

ud = tempfile.mkdtemp(prefix='edge_shot_multi_')
cmd = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--force-device-scale-factor=1',
    f'--user-data-dir={ud}', '--window-size=480,932', '--virtual-time-budget=3000',
    f'--screenshot={p_multi}', 'file:///D:/VINA/static/test_cart_multi.html'
]
res = subprocess.run(cmd, capture_output=True, text=True)
print('p_multi taken:', os.path.exists(p_multi), res.returncode)
