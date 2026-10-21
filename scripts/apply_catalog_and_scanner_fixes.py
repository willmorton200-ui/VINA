# -*- coding: utf-8 -*-
import re

# 1. Update static/scanner.html
with open('d:/VINA/static/scanner.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Update script tag version to v=33
html = re.sub(r'scanner\.js\?v=\d+', 'scanner.js?v=33', html)

# Add robust direct fallback to file-input
old_file_input = '<input type="file" id="file-input" accept="image/*" hidden>'
new_file_input = '<input type="file" id="file-input" accept="image/*" hidden onchange="if(this.files&&this.files[0]&&typeof window.processScannerImageFile===\'function\'){window.processScannerImageFile(this.files[0]);this.value=\'\';}">'
if old_file_input in html:
    html = html.replace(old_file_input, new_file_input, 1)
    print("Patched file-input onchange in scanner.html")

# Patch btn-snap to trigger file picker if camera stream inactive
old_btn_snap = '<button type="button" id="btn-snap" class="scanner-snap-btn-overlay" title="Сделать снимок этикетки">'
new_btn_snap = '<button type="button" id="btn-snap" class="scanner-snap-btn-overlay" title="Сделать снимок этикетки" onclick="if(!window.activeCameraStream && !window.cameraStream){document.getElementById(\'file-input\').click();}">'
if old_btn_snap in html:
    html = html.replace(old_btn_snap, new_btn_snap, 1)
    print("Patched btn-snap in scanner.html")

# Patch renderHomeWineCard to include .home-wine-card-bottom-row with price and button
old_render_home_body = """                    <div class="home-wine-body">
                        <h3 class="home-wine-title">${w.title}</h3>
                        <p class="home-wine-meta">${w.meta}</p>
                        <div class="home-wine-price">${w.price.toLocaleString('ru-RU')} ₽</div>
                    </div>"""

new_render_home_body = """                    <div class="home-wine-body">
                        <h3 class="home-wine-title" title="${w.title}">${w.title}</h3>
                        <p class="home-wine-meta">${w.meta}</p>
                        <div class="home-wine-card-bottom-row">
                            <div class="home-wine-price">${(typeof w.price==='number'?w.price:parseInt(String(w.price).replace(/\\D/g,''),10)||2090).toLocaleString('ru-RU')} ₽</div>
                            <button type="button" class="btn-card-add-cart" onclick="event.stopPropagation(); addWineToCartDirectly('${w.slug}', '${(w.title||'').replace(/'/g, \"\\\\'\")}', ${(typeof w.price==='number'?w.price:parseInt(String(w.price).replace(/\\D/g,''),10)||2090)}, '${imgSrc}', '${(w.meta||'').replace(/'/g, \"\\\\'\")}')" title="Добавить в корзину">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M5 7h14l-1 13H6L5 7z"></path>
                                    <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                                </svg>
                                <span>В корзину</span>
                            </button>
                        </div>
                    </div>"""

if old_render_home_body in html:
    html = html.replace(old_render_home_body, new_render_home_body, 1)
    print("Patched renderHomeWineCard in scanner.html")

# Patch fetchCatalogWines to use exactly matching .home-wine-bottle-wrap and 2-column layout
pattern_cat_card = r"""return `\s*<div class="home-wine-card" onclick="openWineDetail\('\$\{w\.slug\}'\)" style="flex: auto; width: 100%;">.*?</div>\s*</div>\s*`;"""
replacement_cat_card = """const localImg = `../wines_images_clean/wines_images/${w.slug}.webp`;
                    const finalImg = (window.location.protocol === 'file:') ? localImg : photoUrl;

                    return `
                        <div class="home-wine-card catalog-wine-card-2col" onclick="openWineDetail('${w.slug}')">
                            <div class="home-wine-card-top">
                                <div class="home-wine-rating-pill">
                                    <img src="img/glass_filled_straight.png" class="badge-icon-glass-mini" alt="" style="width: 14px; height: 16px; object-fit: contain;">
                                    <span class="home-rating-score">${ratingScore}</span>
                                </div>
                                <button type="button" class="home-fav-btn ${isFav ? 'is-fav' : ''}" data-slug="${w.slug}" onclick="toggleWineFavorite(event, '${w.slug}')" aria-label="В избранное">
                                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>
                                    </svg>
                                </button>
                            </div>
                            <div class="home-wine-bottle-wrap">
                                <img src="${finalImg}" alt="${w.name}" class="home-wine-bottle-img" loading="lazy" onerror="if(this.src.indexOf('wines_images_clean')===-1){this.src='${localImg}';}else{this.src='badge_glass.png';}">
                            </div>
                            <div class="home-wine-body">
                                <h3 class="home-wine-title" title="${w.name}">${w.name}</h3>
                                <p class="home-wine-meta">${metaFormatted}</p>
                                <div class="home-wine-card-bottom-row">
                                    <div class="home-wine-price">${price.toLocaleString('ru-RU')} ₽</div>
                                    <button type="button" class="btn-card-add-cart" onclick="event.stopPropagation(); addWineToCartDirectly('${w.slug}', '${w.name.replace(/'/g, "\\\\'")}', ${price}, '${photoUrl}', '${metaFormatted.replace(/'/g, "\\\\'")}')" title="Добавить в корзину">
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                            <path d="M5 7h14l-1 13H6L5 7z"></path>
                                            <path d="M9 7v-1a3 3 0 0 1 6 0v1"></path>
                                        </svg>
                                        <span>В корзину</span>
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;"""

match = re.search(pattern_cat_card, html, re.DOTALL)
if match:
    html = html[:match.start()] + replacement_cat_card + html[match.end():]
    print("Patched fetchCatalogWines in scanner.html successfully")
else:
    print("Pattern for fetchCatalogWines not found, trying exact substring")

with open('d:/VINA/static/scanner.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Saved scanner.html")
