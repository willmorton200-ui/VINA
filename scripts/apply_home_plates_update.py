import re

# 1. Update static/scanner.css
with open('static/scanner.css', 'r', encoding='utf-8') as f:
    css = f.read()

old_promo_css = '''/* Плашка над поиском на главной: Сканер вин - Узнай Свое вино по фото! */
.home-scanner-promo-bar {
    width: 100%;
    background: linear-gradient(135deg, #800020 0%, #9e1436 100%);
    color: #ffffff;
    border-radius: 14px;
    padding: 13px 16px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 14px rgba(128, 0, 32, 0.22);
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.home-scanner-promo-bar:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(128, 0, 32, 0.3);
}
.home-scanner-promo-left {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 0;
}
.home-scanner-promo-znak {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
}
.home-scanner-promo-text {
    font-size: 14px;
    font-weight: 700;
    color: #ffffff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    letter-spacing: -0.2px;
}
.home-scanner-promo-arrow {
    color: #ffffff;
    opacity: 0.9;
    flex-shrink: 0;
}'''

new_promo_css = '''/* Серые плашки на главной (цвет как в поиске, по центру, шрифт черный, без логотипа) */
.home-action-plate {
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    width: 100%;
    background: #ededf0;
    color: #1a1a1a;
    border-radius: 12px;
    padding: 0 16px;
    height: 44px;
    margin-bottom: 10px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    user-select: none;
    box-shadow: none;
    border: none;
    transition: background-color 0.15s ease, transform 0.1s ease;
}
.home-action-plate:hover {
    background: #e2e2e6;
}
.home-action-plate:active {
    background: #d8d8dc;
    transform: scale(0.99);
}'''

if old_promo_css.replace('\r\n', '\n') in css.replace('\r\n', '\n'):
    if '\r\n' in css:
        css = css.replace(old_promo_css.replace('\n', '\r\n'), new_promo_css.replace('\n', '\r\n'), 1)
    else:
        css = css.replace(old_promo_css, new_promo_css, 1)
    with open('static/scanner.css', 'w', encoding='utf-8', newline='') as f:
        f.write(css)
    print('scanner.css updated with .home-action-plate')
else:
    print('old_promo_css not found in scanner.css, appending...')
    css = css + '\n' + new_promo_css
    with open('static/scanner.css', 'w', encoding='utf-8', newline='') as f:
        f.write(css)
    print('Appended .home-action-plate to scanner.css')

# 2. Update static/scanner.html
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

old_search_block = '''                <!-- Плашка на всю ширину: Сканер вин - Узнай Свое вино по фото! -->
                <div class="home-scanner-promo-bar" onclick="openCameraFromHome()" title="Открыть сканер вин">
                    <div class="home-scanner-promo-left">
                        <img src="znak.png" alt="" class="home-scanner-promo-znak">
                        <span class="home-scanner-promo-text">Сканер вин — Узнай Свое вино по фото!</span>
                    </div>
                    <svg class="home-scanner-promo-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                </div>

                <!-- Строка поиска вина (кнопки «+» и «фотоаппарат» убраны согласно заданию) -->
                <div class="home-search-bar">
                    <svg class="home-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8e8e93" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" onclick="submitHomeSearch()">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <input
                        type="text"
                        id="home-search-input"
                        class="home-search-input"
                        placeholder="Поиск вина в каталоге..."
                        onkeydown="if(event.key==='Enter') submitHomeSearch()"
                    />
                </div>'''

new_search_block = '''                <!-- 1. Строка поиска вина выше -->
                <div class="home-search-bar">
                    <svg class="home-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8e8e93" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" onclick="submitHomeSearch()">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <input
                        type="text"
                        id="home-search-input"
                        class="home-search-input"
                        placeholder="Поиск вина в каталоге..."
                        onkeydown="if(event.key==='Enter') submitHomeSearch()"
                    />
                </div>

                <!-- 2. Плашка Сканер вин ниже (серый цвет как в поиске, по центру, шрифт черный, без логотипа) -->
                <div class="home-action-plate" onclick="openCameraFromHome()" title="Открыть сканер вин">
                    Сканер вин — Узнай Свое вино по фото!
                </div>

                <!-- 3. Плашка Сомелье (серый цвет как в поиске, по центру, шрифт черный) -->
                <div class="home-action-plate" onclick="openSommelierFromHome()" title="Открыть Сомелье">
                    Сомелье
                </div>'''

if old_search_block.replace('\r\n', '\n') in html.replace('\r\n', '\n'):
    if '\r\n' in html:
        html = html.replace(old_search_block.replace('\n', '\r\n'), new_search_block.replace('\n', '\r\n'), 1)
    else:
        html = html.replace(old_search_block, new_search_block, 1)
    print('scanner.html search and action plates updated')
else:
    print('WARNING: old_search_block not found in scanner.html')

# Add openSommelierFromHome in script if not present
if 'function openSommelierFromHome' not in html:
    old_cam_fn = '''        function openCameraFromHome() {
            isCameraPowered = true;
            switchHubTab('scanner');
            if (typeof window.showScannerMainView === 'function') {
                window.showScannerMainView();
            }
            if (typeof window.startScannerCamera === 'function') {
                window.startScannerCamera();
            }
        }'''
    new_cam_fn = '''        function openCameraFromHome() {
            isCameraPowered = true;
            switchHubTab('scanner');
            if (typeof window.showScannerMainView === 'function') {
                window.showScannerMainView();
            }
            if (typeof window.startScannerCamera === 'function') {
                window.startScannerCamera();
            }
        }

        function openSommelierFromHome() {
            if (typeof window.openSommelierEntryPoint === 'function') {
                window.openSommelierEntryPoint('main-home', { name: 'Персональный ИИ-Сомелье' });
            } else {
                switchHubTab('sommelier');
            }
        }
        window.openSommelierFromHome = openSommelierFromHome;'''

    if old_cam_fn.replace('\r\n', '\n') in html.replace('\r\n', '\n'):
        if '\r\n' in html:
            html = html.replace(old_cam_fn.replace('\n', '\r\n'), new_cam_fn.replace('\n', '\r\n'), 1)
        else:
            html = html.replace(old_cam_fn, new_cam_fn, 1)
        print('Added openSommelierFromHome in scanner.html')

with open('static/scanner.html', 'w', encoding='utf-8', newline='') as f:
    f.write(html)
print('scanner.html saved')
