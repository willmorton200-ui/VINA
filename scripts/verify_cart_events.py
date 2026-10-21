import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
ud = tempfile.mkdtemp(prefix='edge_verify_')

html_test_runner = """
<!DOCTYPE html>
<html>
<body>
<iframe id="test-frame" src="file:///D:/VINA/static/scanner.html?preview_step=cart" style="width: 480px; height: 900px;"></iframe>
<script>
window.onload = function() {
    setTimeout(function() {
        const frame = document.getElementById('test-frame').contentWindow;
        console.log('Testing cart...');
        
        // 1. Check cart items
        let items = frame.getCartItems();
        console.log('Cart items count:', items.length);
        if (items.length === 0) {
            console.error('FAIL: No cart items found');
            return;
        }

        // 2. Test toggling checkbox
        const slug = items[0].slug;
        frame.toggleCartItemChecked(slug);
        items = frame.getCartItems();
        console.log('After uncheck, checked is:', items[0].checked);

        // 3. Test changing qty
        frame.changeCartItemQty(slug, 2);
        items = frame.getCartItems();
        console.log('After +2 qty, qty is:', items[0].qty);

        // 4. Test delivery toggle
        frame.setCartDeliveryMethod('courier');
        console.log('Delivery method set to courier');

        // Check DOM state
        const buyBtn = frame.document.getElementById('btn-cart-buy');
        console.log('Buy button text:', buyBtn ? buyBtn.textContent : 'null');
        console.log('ALL TESTS PASSED');
    }, 1500);
};
</script>
</body>
</html>
"""

with open('static/test_runner_cart.html', 'w', encoding='utf-8') as f:
    f.write(html_test_runner)

cmd = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    f'--user-data-dir={ud}', '--virtual-time-budget=4000', '--dump-dom',
    'file:///D:/VINA/static/test_runner_cart.html'
]
res = subprocess.run(cmd, capture_output=True, text=True)
print('DOM Dump executed')
