with open('static/scanner.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("previewStep === 'wine_detail'", "previewStep === 'wine_detail' || previewStep === 'sommelier_stub'")

old_dcl = """            } else if (pStep === 'wine_detail') {
                switchHubTab('catalog');
                openWineDetail('loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131');"""

new_dcl = """            } else if (pStep === 'wine_detail') {
                switchHubTab('catalog');
                openWineDetail('loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131');
            } else if (pStep === 'sommelier_stub') {
                switchHubTab('catalog');
                openWineDetail('loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131');
                setTimeout(function() {
                    if (typeof window.openSommelierEntryPoint === 'function') {
                        window.openSommelierEntryPoint('loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131', { name: 'Loco Cimbali Blanc de Neige' });
                    }
                }, 350);"""

if old_dcl in text:
    text = text.replace(old_dcl, new_dcl, 1)
    print("Added sommelier_stub to DOMContentLoaded")
else:
    print("old_dcl not found")

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(text)
