import re

# 1. Update static/scanner.css
with open('static/scanner.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Replace .scanner-snap-btn-overlay and add .home-scanner-promo-bar, .btn-scanner-choose-photo
old_snap_css = '''.scanner-snap-btn-overlay {
    position: absolute;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    width: 70px;
    height: 70px;
    border-radius: 50%;
    background: #ffffff;
    border: 5px solid var(--primary, #800020);
    box-shadow: 0 6px 22px rgba(0, 0, 0, 0.45);
    cursor: pointer;
    z-index: 20;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.scanner-snap-btn-overlay:hover {
    box-shadow: 0 8px 26px rgba(128, 0, 32, 0.55);
}'''

new_snap_css = '''/* Плашка над поиском на главной: Сканер вин - Узнай Свое вино по фото! */
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
}

/* Круглая кнопка съемки в виде значка znak.png */
.scanner-snap-btn-overlay {
    position: absolute;
    bottom: 86px;
    left: 50%;
    transform: translateX(-50%);
    width: 68px;
    height: 68px;
    border-radius: 50%;
    background: #ffffff;
    border: 3.5px solid #ffffff;
    box-shadow: 0 6px 22px rgba(0, 0, 0, 0.45);
    cursor: pointer;
    z-index: 20;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.scanner-snap-btn-overlay:hover {
    box-shadow: 0 8px 28px rgba(128, 0, 32, 0.6);
    transform: translateX(-50%) scale(1.05);
}
.scanner-snap-btn-overlay:active {
    transform: translateX(-50%) scale(0.95);
}
.scanner-snap-znak-img {
    width: 100%;
    height: 100%;
    border-radius: 50%;
    object-fit: cover;
    display: block;
}

/* Бордовая кнопка внизу сканера на всю ширину «Выбрать фото» */
.btn-scanner-choose-photo {
    position: absolute;
    bottom: 20px;
    left: 20px;
    right: 20px;
    height: 48px;
    background: var(--primary, #800020);
    color: #ffffff;
    border: none;
    border-radius: 12px;
    font-size: 15px;
    font-weight: 700;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    cursor: pointer;
    z-index: 20;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}
.btn-scanner-choose-photo:hover {
    background: var(--primary-light, #a31c3b);
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(128, 0, 32, 0.4);
}
.btn-scanner-choose-photo:active {
    transform: translateY(0);
}'''

if old_snap_css.replace('\r\n', '\n') in css.replace('\r\n', '\n'):
    if '\r\n' in css:
        css = css.replace(old_snap_css.replace('\n', '\r\n'), new_snap_css.replace('\n', '\r\n'), 1)
    else:
        css = css.replace(old_snap_css, new_snap_css, 1)
    with open('static/scanner.css', 'w', encoding='utf-8', newline='') as f:
        f.write(css)
    print('scanner.css updated successfully')
else:
    print('old_snap_css not matched exactly, checking...')

# 2. Update static/scanner.html
with open('static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Update checkCachedOnboarding and health fetch to keep splash screens always visible for demo
old_cache_fn = '''            function checkCachedOnboarding(bootId) {
                try {
                    var done = localStorage.getItem('svoe_vino_onboard_done');
                    var savedBoot = localStorage.getItem('svoe_vino_boot_id');
                    if (done === '1' && (!bootId || savedBoot === bootId)) {
                        if (splash) {
                            splash.classList.add('hidden-gate');
                            splash.style.display = 'none';
                            splash.querySelectorAll('.active-step').forEach(function(el) { el.classList.remove('active-step'); });
                        }
                        document.body.style.overflow = '';
                        return true;
                    } else {
                        if (bootId && savedBoot !== bootId) {
                            localStorage.removeItem('svoe_vino_onboard_done');
                            localStorage.setItem('svoe_vino_boot_id', bootId);
                        }
                        if (splash) {
                            splash.classList.remove('hidden-gate');
                            splash.style.display = '';
                        }
                        document.body.style.overflow = 'hidden';
                        return false;
                    }
                } catch (e) {
                    return false;
                }
            }'''

new_cache_fn = '''            function checkCachedOnboarding(bootId) {
                try {
                    // Для постоянной демонстрации приложения начальные заставки показываются всегда при загрузке
                    if (splash) {
                        splash.classList.remove('hidden-gate');
                        splash.style.display = '';
                        splash.querySelectorAll('.active-step, .active-sheet, .active-auth, .active-substep').forEach(function(el) {
                            el.classList.remove('active-step', 'active-sheet', 'active-auth', 'active-substep');
                        });
                        var s1 = document.getElementById('splash-step-1');
                        if (s1) s1.classList.add('active-step');
                    }
                    document.body.style.overflow = 'hidden';
                    return false;
                } catch (e) {
                    return false;
                }
            }'''

if old_cache_fn.replace('\r\n', '\n') in html.replace('\r\n', '\n'):
    if '\r\n' in html:
        html = html.replace(old_cache_fn.replace('\n', '\r\n'), new_cache_fn.replace('\n', '\r\n'), 1)
    else:
        html = html.replace(old_cache_fn, new_cache_fn, 1)
    print('Updated checkCachedOnboarding in scanner.html')

# In health fetch, do not auto-close splash
old_health_close = '''                    var done = localStorage.getItem('svoe_vino_onboard_done');
                    if (done === '1' && savedBoot === currentBootId) {
                        if (splash) {
                            splash.classList.add('hidden-gate');
                            splash.style.display = 'none';
                            splash.querySelectorAll('.active-step').forEach(function(el) { el.classList.remove('active-step'); });
                        }
                        document.body.style.overflow = '';
                    } else if (savedBoot && savedBoot !== currentBootId) {'''

new_health_close = '''                    // Для постоянной демонстрации заставки не скрываются автоматически через health-check
                    if (savedBoot && savedBoot !== currentBootId) {'''

if old_health_close.replace('\r\n', '\n') in html.replace('\r\n', '\n'):
    if '\r\n' in html:
        html = html.replace(old_health_close.replace('\n', '\r\n'), new_health_close.replace('\n', '\r\n'), 1)
    else:
        html = html.replace(old_health_close, new_health_close, 1)
    print('Updated health-check in scanner.html')

# Update Home page search bar and add full-width promo bar above it
old_home_search = '''                <!-- Строка поиска вина + кнопка "+" (галерея/файлы) + кнопка фотоаппарата (камера сканера) -->
                <div class="home-search-bar">
                    <svg class="home-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8e8e93" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" onclick="submitHomeSearch()">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <input
                        type="text"
                        id="home-search-input"
                        class="home-search-input"
                        placeholder="новинки"
                        onkeydown="if(event.key==='Enter') submitHomeSearch()"
                    />
                    <label class="home-search-action-btn home-plus-btn" title="Выбрать фото бутылки из галереи или с компьютера для распознавания">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
                            <line x1="12" y1="5" x2="12" y2="19"></line>
                            <line x1="5" y1="12" x2="19" y2="12"></line>
                        </svg>
                        <input type="file" id="home-gallery-input" accept="image/*" hidden onchange="onHomeGalleryFileSelected(this)">
                    </label>
                    <button type="button" class="home-search-action-btn home-cam-btn" onclick="openCameraFromHome()" title="Включить камеру для распознавания этикетки">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
                            <circle cx="12" cy="13" r="4"></circle>
                        </svg>
                    </button>
                </div>'''

new_home_search = '''                <!-- Плашка на всю ширину: Сканер вин - Узнай Свое вино по фото! -->
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
                </div>
                <!-- Скрытый инпут галереи оставлен для совместимости -->
                <input type="file" id="home-gallery-input" accept="image/*" hidden onchange="onHomeGalleryFileSelected(this)">'''

if old_home_search.replace('\r\n', '\n') in html.replace('\r\n', '\n'):
    if '\r\n' in html:
        html = html.replace(old_home_search.replace('\n', '\r\n'), new_home_search.replace('\n', '\r\n'), 1)
    else:
        html = html.replace(old_home_search, new_home_search, 1)
    print('Updated Home search and added promo bar in scanner.html')

# Update Scanner View: snap button with znak.png and full-width Choose Photo button below
old_scanner_frame = '''                    <!-- Круглая кнопка съемки прямо на экране камеры -->
                    <button type="button" id="btn-snap" class="scanner-snap-btn-overlay" title="Сделать снимок этикетки"></button>
                </div>'''

new_scanner_frame = '''                    <!-- Круглая кнопка съемки в виде значка znak.png (перенесена чуть выше) -->
                    <button type="button" id="btn-snap" class="scanner-snap-btn-overlay" title="Сделать снимок этикетки">
                        <img src="znak.png" alt="Съемка" class="scanner-snap-znak-img">
                    </button>

                    <!-- Бордовая кнопка внизу на всю ширину «Выбрать фото» -->
                    <button type="button" class="btn-scanner-choose-photo" id="btn-scanner-choose-photo" onclick="document.getElementById('file-input').click()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                            <circle cx="8.5" cy="8.5" r="1.5"></circle>
                            <polyline points="21 15 16 10 5 21"></polyline>
                        </svg>
                        <span>Выбрать фото</span>
                    </button>
                </div>'''

if old_scanner_frame.replace('\r\n', '\n') in html.replace('\r\n', '\n'):
    if '\r\n' in html:
        html = html.replace(old_scanner_frame.replace('\n', '\r\n'), new_scanner_frame.replace('\n', '\r\n'), 1)
    else:
        html = html.replace(old_scanner_frame, new_scanner_frame, 1)
    print('Updated Scanner buttons in scanner.html')

with open('static/scanner.html', 'w', encoding='utf-8', newline='') as f:
    f.write(html)
print('Finished updating scanner.html')
