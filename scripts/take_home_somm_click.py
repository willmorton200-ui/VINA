import subprocess, tempfile, os

edge = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
out_dir = r'C:\Users\User\.gemini\antigravity\brain\1edcd60d-9672-4ec5-8dc2-324e955c1616'

ud1 = tempfile.mkdtemp(prefix='edge_shot_home_somm_')
p1 = os.path.join(out_dir, 'preview_home_sommelier_modal.png')

# HTML script that opens scanner.html?preview_step=home, then clicks the Sommelier plate
html_test = """
<!DOCTYPE html>
<html>
<body style="margin:0; padding:0;">
<iframe id="test-frame" src="scanner.html?preview_step=home" style="width: 480px; height: 932px; border: none;"></iframe>
<script>
window.onload = function() {
    setTimeout(function() {
        const frame = document.getElementById('test-frame').contentWindow;
        if (typeof frame.openSommelierFromHome === 'function') {
            frame.openSommelierFromHome();
        }
    }, 500);
};
</script>
</body>
</html>
"""

with open('static/test_home_somm.html', 'w', encoding='utf-8') as f:
    f.write(html_test)

cmd1 = [
    edge, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--force-device-scale-factor=1',
    f'--user-data-dir={ud1}', '--window-size=480,932', '--virtual-time-budget=3000',
    f'--screenshot={p1}', 'file:///D:/VINA/static/test_home_somm.html'
]
res1 = subprocess.run(cmd1, capture_output=True, text=True)
print('p1 (home somm modal):', p1, os.path.exists(p1), res1.returncode)
