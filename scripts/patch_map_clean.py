with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Remove map icon and align text in map panel header
old_map_header = """                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        <h3 style="margin: 0; font-size: 17px; color: #1a1a1a; display: flex; align-items: center; gap: 8px;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
                                <line x1="8" y1="2" x2="8" y2="18"></line>
                                <line x1="16" y1="6" x2="16" y2="22"></line>
                            </svg>
                            5 ближайших магазинов пешком
                        </h3>
                        <p id="map-target-wine-label" style="font-size: 12px; color: var(--primary); margin-top: 3px; font-weight: 600;">
                            Выберите магазин и нажмите «Путь» — построится пеший маршрут с GPS-трекингом
                        </p>
                    </div>
                    <button class="btn btn-secondary" onclick="centerMapOnUser()" style="padding: 7px 12px; font-size: 12px;">Где я</button>
                </div>"""

new_map_header = """                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; gap: 12px;">
                    <div style="flex: 1;">
                        <h3 style="margin: 0; font-size: 18px; font-weight: 700; color: #1a1a1a; line-height: 1.25;">5 ближайших магазинов пешком</h3>
                        <p id="map-target-wine-label" style="font-size: 13px; color: #722F37; margin: 5px 0 0 0; font-weight: 600; line-height: 1.35;">
                            Выберите магазин и нажмите «Путь» — построится пеший маршрут с GPS-трекингом
                        </p>
                    </div>
                    <button class="btn btn-secondary" onclick="centerMapOnUser()" style="padding: 8px 14px; font-size: 13px; font-weight: 600; border-radius: 10px; flex-shrink: 0;">Где я</button>
                </div>"""

assert old_map_header in html, "old_map_header not found"
html = html.replace(old_map_header, new_map_header, 1)

# 2. Disable Leaflet attribution (removes Ukrainian flag and Leaflet links)
old_init_map = """        function initVinaOsmMap() {
            if (!osmMapInstance) {
                osmMapInstance = L.map('vina-osm-map').setView([userLatitude, userLongitude], 15);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19,
                    attribution: '© OpenStreetMap'
                }).addTo(osmMapInstance);
            }"""

new_init_map = """        function initVinaOsmMap() {
            if (!osmMapInstance) {
                osmMapInstance = L.map('vina-osm-map', {
                    attributionControl: false
                }).setView([userLatitude, userLongitude], 15);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    maxZoom: 19
                }).addTo(osmMapInstance);
            }"""

assert old_init_map in html, "old_init_map not found"
html = html.replace(old_init_map, new_init_map, 1)

# 3. Remove store name label on map markers, leaving only the glass + number
old_store_icon = """                    // Места винных магазинов на карте отмечаем полными бокалами (иконка большая из оценки) + номер + название
                    const storeIcon = L.divIcon({
                        className: 'vina-map-glass-marker',
                        html: `
                            <div class="vina-map-marker-inner" id="map-pin-${s.store_id}">
                                <div class="vina-marker-glass-wrap">
                                    <img src="img/glass_filled_straight.png" class="vina-marker-glass-icon" alt="">
                                    <span class="vina-marker-badge-num">${idx + 1}</span>
                                </div>
                                <div class="vina-marker-label-name">${s.name}</div>
                            </div>
                        `,
                        iconSize: [120, 68],
                        iconAnchor: [60, 50]
                    });"""

new_store_icon = """                    // Места винных магазинов на карте: только бокал и крупный номер (без длинных названий)
                    const storeIcon = L.divIcon({
                        className: 'vina-map-glass-marker',
                        html: `
                            <div class="vina-map-marker-inner" id="map-pin-${s.store_id}">
                                <div class="vina-marker-glass-wrap">
                                    <img src="img/glass_filled_straight.png" class="vina-marker-glass-icon" alt="">
                                    <span class="vina-marker-badge-num">${idx + 1}</span>
                                </div>
                            </div>
                        `,
                        iconSize: [44, 52],
                        iconAnchor: [22, 48]
                    });"""

assert old_store_icon in html, "old_store_icon not found"
html = html.replace(old_store_icon, new_store_icon, 1)

# 4. Bump version strings
html = html.replace('scanner.css?v=42_cathead', 'scanner.css?v=43_cleanmap', 1)
html = html.replace('scanner.js?v=37_cathead', 'scanner.js?v=38_cleanmap', 1)

with open('static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated scanner.html successfully!")
