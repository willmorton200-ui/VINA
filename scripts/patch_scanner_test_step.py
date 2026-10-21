with open('d:/VINA/static/scanner.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("previewStep === 'scanner' ||", "previewStep === 'scanner' || previewStep === 'scanner_test' ||", 1)

old_step = "} else if (pStep === 'scanner') {\n                switchHubTab('scanner');"
new_step = """} else if (pStep === 'scanner') {
                switchHubTab('scanner');
            } else if (pStep === 'scanner_test') {
                switchHubTab('scanner');
                setTimeout(async () => {
                    try {
                        const blobRes = await fetch('../wines_images_clean/wines_images/loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131.webp');
                        const blob = await blobRes.blob();
                        const file = new File([blob], 'loco-cimbali.webp', { type: 'image/webp' });
                        if (typeof window.processScannerImageFile === 'function') {
                            window.processScannerImageFile(file);
                        }
                    } catch (e) {
                        console.error(e);
                    }
                }, 400);"""

text = text.replace(old_step, new_step, 1)

with open('d:/VINA/static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated scanner.html with scanner_test')
