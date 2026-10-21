with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace("previewStep === 'wine_detail'", "previewStep === 'wine_detail' || previewStep === 'wine_detail_map_click'", 1)

old_step = """            } else if (pStep === 'wine_detail') {
                switchHubTab('catalog');
                openWineDetail('loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131');"""

new_step = """            } else if (pStep === 'wine_detail') {
                switchHubTab('catalog');
                openWineDetail('loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131');
            } else if (pStep === 'wine_detail_map_click') {
                switchHubTab('catalog');
                openWineDetail('loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131');
                setTimeout(function() {
                    var btnMap = document.getElementById('btn-detail-sticky-map');
                    if (btnMap) btnMap.click();
                }, 400);"""

assert old_step in html, "old_step not found"
html = html.replace(old_step, new_step, 1)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Added wine_detail_map_click preview step")
