with open('d:/VINA/static/scanner.html', 'r', encoding='utf-8') as f:
    text = f.read()

old = "fetch('../wines_images_clean/wines_images/loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131.webp');"
new = "fetch('/api/image/loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131');"

if old in text:
    text = text.replace(old, new, 1)
    with open('d:/VINA/static/scanner.html', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Updated image fetch URL in scanner_test')
else:
    print('Old fetch URL not found')
