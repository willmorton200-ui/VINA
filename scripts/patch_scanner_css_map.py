with open('static/scanner.css', 'r', encoding='utf-8') as f:
    css = f.read()

target = """.vina-marker-label-name {
    margin-top: 3px;
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #722F37;
    border-radius: 8px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 700;
    color: #1a1a1a;
    white-space: nowrap;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}"""

replacement = """.vina-marker-label-name {
    display: none !important;
}

/* Полное скрытие копирайтов и флагов Leaflet */
.leaflet-control-attribution,
.leaflet-bottom.leaflet-right {
    display: none !important;
    visibility: hidden !important;
}"""

assert target in css, "target not found in scanner.css"
css = css.replace(target, replacement, 1)

with open('static/scanner.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("Updated scanner.css with hidden attribution and label name!")
