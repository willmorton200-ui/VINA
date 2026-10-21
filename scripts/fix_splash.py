with open('static/scanner.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("previewStep === 'map'", "previewStep === 'map' || previewStep === 'wine_detail'")

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(text)
print('Added wine_detail to splash bypass')
