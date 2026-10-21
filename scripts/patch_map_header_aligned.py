with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = """                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; gap: 12px;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1a1a1a; line-height: 1.25;">5 ближайших магазинов пешком</h3>
                        <p id="map-target-wine-label" style="font-size: 13px; color: #722F37; margin: 5px 0 0 0; font-weight: 600; line-height: 1.35;">
                            Выберите магазин и нажмите «Путь» — построится пеший маршрут с GPS-трекингом
                        </p>
                    </div>
                    <button class="btn btn-secondary" onclick="centerMapOnUser()" style="padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 10px; flex-shrink: 0;">Где я</button>
                </div>"""

replacement = """                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; gap: 12px;">
                    <div style="flex: 1; min-width: 0;">
                        <h3 style="margin: 0; font-size: 17px; font-weight: 700; color: #1a1a1a; line-height: 1.25; white-space: nowrap;">5 ближайших магазинов пешком</h3>
                        <p id="map-target-wine-label" style="font-size: 12px; color: #722F37; margin: 4px 0 0 0; font-weight: 600; line-height: 1.35;">
                            Выберите магазин и нажмите «Путь» — построится пеший маршрут с GPS-трекингом
                        </p>
                    </div>
                    <button type="button" class="btn-map-locate-user" onclick="centerMapOnUser()">Где я</button>
                </div>"""

assert target in html, "target not found in scanner.html"
html = html.replace(target, replacement, 1)

# Bump version
html = html.replace('scanner.css?v=43_cleanmap', 'scanner.css?v=44_mapfix', 1)
html = html.replace('scanner.js?v=38_cleanmap', 'scanner.js?v=39_mapfix', 1)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated scanner.html with aligned map header and clean button!")

with open('static/scanner.css', 'r', encoding='utf-8') as f:
    css = f.read()

btn_css = """
.btn-map-locate-user {
    flex: 0 0 auto !important;
    width: auto !important;
    max-width: fit-content !important;
    background: #ededf0 !important;
    color: #1a1a1a !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 7px 14px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    transition: background 0.15s ease !important;
}

.btn-map-locate-user:hover {
    background: #e2e2e7 !important;
}
"""

if ".btn-map-locate-user" not in css:
    css += btn_css
    with open('static/scanner.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print("Added .btn-map-locate-user CSS!")
