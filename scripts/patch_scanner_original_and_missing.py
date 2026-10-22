# -*- coding: utf-8 -*-
"""Patch script for scanner.html and scanner.js to implement original photo comparison and missing wine flow."""

# -------------------------------------------------------------
# 1. PATCH static/scanner.html
# -------------------------------------------------------------
with open("static/scanner.html", "r", encoding="utf-8") as f:
    html = f.read()

# 1.1 Update showScanOriginalPhoto and backToWineDetailFromOriginalPhoto
target_nav = """        function showScanOriginalPhoto() {
            const detailView = document.getElementById('catalog-detail-view');
            const originalView = document.getElementById('original-view');
            if (detailView) detailView.style.display = 'none';
            switchHubTab('scanner');
            if (typeof window.showView === 'function') {
                window.showView(originalView);
            } else if (originalView) {
                document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
                originalView.classList.add('active');
            }
        }

        function backToWineDetailFromOriginalPhoto() {
            if (window.currentDetailWineSlug) {
                openWineDetail(window.currentDetailWineSlug, 'scanner');
            } else {
                switchHubTab('scanner');
            }
        }"""

replacement_nav = """        function showScanOriginalPhoto() {
            const detailView = document.getElementById('catalog-detail-view');
            const originalView = document.getElementById('original-view');
            if (detailView) detailView.style.display = 'none';

            // Гарантируем загрузку исходного фото пользователя
            const photoUrl = window.currentUploadedImageURL || window.lastScannedPhotoDataUrl || sessionStorage.getItem('vina_last_scanned_photo') || '';
            const origImg = document.getElementById('original-img');
            if (origImg && photoUrl) {
                origImg.src = photoUrl;
            }

            // Наполняем эталон каталога для сравнения
            const refImg = document.getElementById('original-catalog-ref-img');
            const slug = window.currentDetailWineSlug || window.lastScannedSlug || '';
            if (refImg && slug) {
                const apiBase = (typeof getHubApiBase === 'function') ? getHubApiBase() : (typeof apiUrl === 'function' ? apiUrl('') : '');
                refImg.src = `${apiBase}/api/image/${slug}`;
            }

            const titleEl = document.getElementById('original-wine-name');
            const wineryEl = document.getElementById('original-wine-winery');
            if (titleEl) titleEl.textContent = document.getElementById('detail-wine-title')?.textContent || 'Найденное вино';
            if (wineryEl) wineryEl.textContent = document.getElementById('detail-wine-winery')?.textContent || '';

            switchHubTab('scanner');
            if (typeof window.showView === 'function') {
                window.showView(originalView);
            } else if (originalView) {
                document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
                originalView.classList.add('active');
            }
        }

        function backToWineDetailFromOriginalPhoto() {
            const slug = window.currentDetailWineSlug || window.lastScannedSlug || '';
            if (slug && typeof window.openWineDetail === 'function') {
                window.openWineDetail(slug, 'scanner');
            } else {
                switchHubTab('scanner');
            }
        }

        function reportIncorrectMatchPrompt() {
            if (confirm("Сообщить разработчикам, что это другое вино, для уточнения базы?")) {
                const photoUrl = window.currentUploadedImageURL || window.lastScannedPhotoDataUrl || sessionStorage.getItem('vina_last_scanned_photo') || '';
                const slug = window.currentDetailWineSlug || window.lastScannedSlug || '';
                const apiBase = (typeof getHubApiBase === 'function') ? getHubApiBase() : (typeof apiUrl === 'function' ? apiUrl('') : '');
                fetch(`${apiBase}/api/missing-wines/report`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source: 'scanner_incorrect_match',
                        query_text: `Пользователь отметил неверное распознавание вина (система определила: ${slug})`,
                        image_base64: (photoUrl && photoUrl.startsWith('data:')) ? photoUrl : undefined
                    })
                }).catch(e => console.warn(e));
                alert("Спасибо! Снимок передан разработчикам для калибровки распознавания.");
            }
        }"""

assert target_nav in html, "target_nav not found in scanner.html"
html = html.replace(target_nav, replacement_nav, 1)

# 1.2 Replace original-view with two-card comparison view
target_orig_view = """            <!-- Original Photo View -->
            <main id="original-view" class="view" style="padding: 16px 20px 30px 20px;">
                <div class="result-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <button class="btn-back" id="btn-back-to-result" onclick="backToWineDetailFromOriginalPhoto()" style="margin-bottom: 0;">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M15 18l-6-6 6-6" />
                        </svg>
                        Назад к вину
                    </button>
                </div>
                <div class="wine-card" style="padding: 12px; text-align: center;">
                    <div class="wine-image-container" style="max-height: 70vh; display: flex; align-items: center; justify-content: center;">
                        <img id="original-img" src="" alt="Original Photo" style="cursor: zoom-in; max-height: 65vh; border-radius: 12px; object-fit: contain;">
                    </div>
                </div>
            </main>"""

replacement_orig_view = """            <!-- Original Photo & Comparison View -->
            <main id="original-view" class="view" style="padding: 14px 16px 36px 16px; max-width: 480px; margin: 0 auto;">
                <div class="result-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <button class="btn-back" id="btn-back-to-result" onclick="backToWineDetailFromOriginalPhoto()" style="margin-bottom: 0; background: #ffffff; border: 1px solid #dee2e6; border-radius: 10px; padding: 7px 12px; font-size: 13px; font-weight: 600; color: #1a1a1a; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M15 18l-6-6 6-6" />
                        </svg>
                        Назад к вину
                    </button>
                    <span style="font-size: 13.5px; font-weight: 700; color: #722F37;">Сравнение этикеток</span>
                </div>

                <!-- Карточка сводки найденного вина -->
                <div id="comparison-wine-summary" style="background: #ffffff; border: 1px solid #e9ecef; border-radius: 14px; padding: 10px 14px; margin-bottom: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.04); display: flex; align-items: center; justify-content: space-between;">
                    <div style="flex: 1; padding-right: 10px;">
                        <div id="original-wine-name" style="font-size: 13.5px; font-weight: 700; color: #1a1a1a; line-height: 1.3;">Найденное вино</div>
                        <div id="original-wine-winery" style="font-size: 12px; color: #6c757d; margin-top: 2px;">Винодельня</div>
                    </div>
                    <div id="original-wine-badge" style="background: #e8f5e9; color: #2e7d32; font-size: 11.5px; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid #c8e6c9; white-space: nowrap;">
                        Распознано
                    </div>
                </div>

                <!-- Блок сравнения двух изображений: Ваше фото vs Каталог -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px;">
                    <!-- Карточка 1: Ваше фото -->
                    <div class="wine-card" style="padding: 10px; text-align: center; margin: 0; display: flex; flex-direction: column; background: #fff; border: 1px solid #e9ecef; border-radius: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
                        <div style="font-size: 11.5px; font-weight: 700; color: #722F37; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                            Ваш снимок
                        </div>
                        <div class="wine-image-container" style="flex: 1; min-height: 220px; max-height: 48vh; display: flex; align-items: center; justify-content: center; background: #f8f9fa; border-radius: 10px; overflow: hidden; position: relative;">
                            <img id="original-img" src="" alt="Ваш снимок с камеры" style="cursor: zoom-in; max-width: 100%; max-height: 46vh; object-fit: contain; border-radius: 8px;" onclick="if(this.src) openLightbox(this.src, 'Ваш снимок с камеры')">
                        </div>
                        <div style="font-size: 10.5px; color: #868e96; margin-top: 6px;">
                            Нажмите для зума
                        </div>
                    </div>

                    <!-- Карточка 2: Эталон из каталога -->
                    <div class="wine-card" style="padding: 10px; text-align: center; margin: 0; display: flex; flex-direction: column; background: #fff; border: 1px solid #e9ecef; border-radius: 14px; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
                        <div style="font-size: 11.5px; font-weight: 700; color: #1e3a8a; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;">
                            Эталон базы
                        </div>
                        <div class="wine-image-container" style="flex: 1; min-height: 220px; max-height: 48vh; display: flex; align-items: center; justify-content: center; background: #f8f9fa; border-radius: 10px; overflow: hidden; position: relative;">
                            <img id="original-catalog-ref-img" src="" alt="Эталонная бутылка из базы" style="cursor: zoom-in; max-width: 100%; max-height: 46vh; object-fit: contain; border-radius: 8px;" onclick="if(this.src) openLightbox(this.src, 'Эталонная бутылка из базы VINA')">
                        </div>
                        <div style="font-size: 10.5px; color: #868e96; margin-top: 6px;">
                            Фото из каталога
                        </div>
                    </div>
                </div>

                <!-- Кнопки внизу -->
                <div style="display: flex; gap: 10px;">
                    <button type="button" class="btn btn-primary" onclick="backToWineDetailFromOriginalPhoto()" style="flex: 1; padding: 12px; font-size: 13.5px; font-weight: 600; border-radius: 12px; background: #722F37; color: #fff; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;">
                        <span>Вернуться к карточке</span>
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="reportIncorrectMatchPrompt()" style="padding: 12px 14px; font-size: 12.5px; font-weight: 600; border-radius: 12px; background: #ffffff; color: #495057; border: 1px solid #ced4da; cursor: pointer; white-space: nowrap;">
                        Это другое вино?
                    </button>
                </div>
            </main>"""

assert target_orig_view in html, "target_orig_view not found in scanner.html"
html = html.replace(target_orig_view, replacement_orig_view, 1)

# 1.3 Replace missing-wine-modal
target_missing = """    <!-- МОДАЛЬНОЕ ОКНО: ВИНО НЕ НАЙДЕНО В КАТАЛОГЕ (ЛОГГИРОВАНИЕ И УВЕДОМЛЕНИЕ) -->
    <div class="missing-wine-modal-overlay" id="missing-wine-modal" onclick="if(event.target.id==='missing-wine-modal') closeMissingWineModal()">
        <div class="missing-wine-modal-card">
            <div class="missing-wine-icon-wrap">
                <img src="svg/public-rating.svg" class="missing-wine-icon-img" alt="" style="width: 32px; height: 32px; object-fit: contain;">
            </div>
            <h3 class="missing-wine-title">Вино не найдено</h3>
            <p class="missing-wine-text" id="missing-wine-message">
                Данного вина пока нет в каталоге, скоро появится, спасибо за проявленный интерес.
            </p>
            <div class="missing-wine-subtext">
                Фотография этикетки и запрос автоматически сохранены и переданы администрации сервиса. Эксперты внесут карточку в базу в ближайшее обновление.
            </div>
            <div style="display: flex; gap: 10px; margin-top: 18px;">
                <button class="btn btn-secondary" onclick="closeMissingWineModal()" style="flex: 1; border-radius: 12px; padding: 12px; font-weight: 600; border: 1px solid #ced4da;">
                    Понятно
                </button>
                <button class="btn btn-primary" onclick="openSommelierFromMissingWine()" style="flex: 1.4; border-radius: 12px; padding: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 6px;">
                    <img src="svg/public-rating.svg" class="badge-icon-glass-mini" style="width: 18px; height: 18px; object-fit: contain; filter: brightness(0) invert(1);" alt="">
                    <span>Спросить сомелье</span>
                </button>
            </div>
        </div>
    </div>"""

replacement_missing = """    <!-- МОДАЛЬНОЕ ОКНО: ВИНО НЕ НАЙДЕНО В КАТАЛОГЕ (ЛОГГИРОВАНИЕ И УВЕДОМЛЕНИЕ) -->
    <div class="missing-wine-modal-overlay" id="missing-wine-modal" onclick="if(event.target.id==='missing-wine-modal') closeMissingWineModal()">
        <div class="missing-wine-modal-card" style="padding: 20px 18px; max-width: 400px;">
            <!-- Превью сделанной фотографии -->
            <div id="missing-wine-photo-box" style="position: relative; width: 100%; max-height: 220px; border-radius: 14px; overflow: hidden; background: #f8f9fa; border: 1px solid #dee2e6; margin-bottom: 14px; display: flex; align-items: center; justify-content: center;">
                <img id="missing-wine-photo-preview" src="" alt="Ваш снимок вина" style="max-height: 220px; max-width: 100%; object-fit: contain; cursor: zoom-in;" onclick="if(this.src) openLightbox(this.src, 'Ваш снимок вина')">
                <div style="position: absolute; top: 8px; left: 8px; background: rgba(0,0,0,0.65); color: #fff; font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 6px; backdrop-filter: blur(4px);">
                    Ваш снимок
                </div>
            </div>

            <!-- Точный текст уведомления по запросу Алексея -->
            <h3 class="missing-wine-title" style="font-size: 16px; font-weight: 700; color: #1a1a1a; margin: 0 0 8px 0; line-height: 1.35;">
                Данного вина нет в базе, отправить разработчику для добавления в базу?
            </h3>
            <p class="missing-wine-subtext" style="font-size: 12px; color: #6c757d; margin: 0 0 16px 0; line-height: 1.45;">
                Разработчики получат снимок этикетки, распознают сорт и винодельню и внесут карточку в каталог VINA.
            </p>

            <!-- Кнопки действий -->
            <div id="missing-wine-actions" style="display: flex; flex-direction: column; gap: 8px;">
                <button id="btn-submit-missing-wine" type="button" class="btn btn-primary" onclick="submitMissingWineToDevs()" style="width: 100%; border-radius: 12px; padding: 13px; font-weight: 700; font-size: 14px; background: #722F37; color: #ffffff; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 2px 8px rgba(114,47,55,0.25);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                    </svg>
                    <span>Отправить разработчику</span>
                </button>
                <div style="display: flex; gap: 8px;">
                    <button type="button" class="btn btn-secondary" onclick="closeMissingWineModal()" style="flex: 1; border-radius: 12px; padding: 11px; font-weight: 600; font-size: 13px; border: 1px solid #ced4da; background: #fff; color: #495057; cursor: pointer;">
                        Отмена
                    </button>
                    <button type="button" class="btn btn-secondary" onclick="openSommelierFromMissingWine()" style="flex: 1.2; border-radius: 12px; padding: 11px; font-weight: 600; font-size: 13px; border: 1px solid #f8d7da; background: #fdf2f4; color: #722F37; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px;">
                        <img src="svg/public-rating.svg" style="width: 16px; height: 16px; object-fit: contain;">
                        <span>Спросить сомелье</span>
                    </button>
                </div>
            </div>

            <!-- Состояние успешной отправки -->
            <div id="missing-wine-success" style="display: none; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 12px; padding: 14px; text-align: center; color: #2e7d32;">
                <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">✓ Отправлено разработчикам!</div>
                <div style="font-size: 12px; color: #388e3c; margin-bottom: 12px;">Спасибо! Снимок передан команде разработки. Мы внесем карточку в каталог.</div>
                <button type="button" class="btn btn-primary" onclick="closeMissingWineModal()" style="border-radius: 10px; padding: 9px 18px; font-size: 13px; font-weight: 600; background: #2e7d32; color: #fff; border: none; cursor: pointer;">
                    Сделать новый снимок
                </button>
            </div>
        </div>
    </div>"""

assert target_missing in html, "target_missing not found in scanner.html"
html = html.replace(target_missing, replacement_missing, 1)

# 1.4 Update showMissingWineModal and add submitMissingWineToDevs in scanner.html script block
target_missing_func = """        function showMissingWineModal(msg) {
            const modal = document.getElementById('missing-wine-modal');
            const msgEl = document.getElementById('missing-wine-message');
            if (msgEl && msg) msgEl.textContent = msg;
            if (modal) modal.style.display = 'flex';
        }

        function closeMissingWineModal() {
            const modal = document.getElementById('missing-wine-modal');
            if (modal) modal.style.display = 'none';
        }"""

replacement_missing_func = """        function showMissingWineModal(msg) {
            const modal = document.getElementById('missing-wine-modal');
            const photoEl = document.getElementById('missing-wine-photo-preview');
            const photoUrl = window.currentUploadedImageURL || window.lastScannedPhotoDataUrl || sessionStorage.getItem('vina_last_scanned_photo') || '';
            if (photoEl) {
                if (photoUrl) {
                    photoEl.src = photoUrl;
                    if (photoEl.parentElement) photoEl.parentElement.style.display = 'flex';
                } else if (photoEl.parentElement) {
                    photoEl.parentElement.style.display = 'none';
                }
            }
            const actions = document.getElementById('missing-wine-actions');
            const success = document.getElementById('missing-wine-success');
            const btn = document.getElementById('btn-submit-missing-wine');
            if (actions) actions.style.display = 'flex';
            if (success) success.style.display = 'none';
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg><span>Отправить разработчику</span>`;
            }
            if (modal) modal.style.display = 'flex';
        }

        function closeMissingWineModal() {
            const modal = document.getElementById('missing-wine-modal');
            if (modal) modal.style.display = 'none';
            if (typeof window.showView === 'function' && window.scannerView) {
                window.showView(window.scannerView);
            }
        }

        async function submitMissingWineToDevs() {
            const btn = document.getElementById('btn-submit-missing-wine');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="somm-spinner" style="border-top-color:#fff;"></span> Отправка...';
            }
            const photoUrl = window.currentUploadedImageURL || window.lastScannedPhotoDataUrl || sessionStorage.getItem('vina_last_scanned_photo') || '';
            const reqId = window.lastMissingReqId || null;
            const ocr = window.lastScannedOcrText || '';

            try {
                const apiBase = (typeof getHubApiBase === 'function') ? getHubApiBase() : (typeof apiUrl === 'function' ? apiUrl('') : '');
                await fetch(`${apiBase}/api/missing-wines/report`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source: 'scanner',
                        query_text: ocr ? `OCR: ${ocr}` : 'Запрос на добавление вина через сканер',
                        req_id: reqId,
                        image_base64: (photoUrl && photoUrl.startsWith('data:')) ? photoUrl : undefined
                    })
                });
            } catch (e) {
                console.warn('submitMissingWine error:', e);
            }

            const actions = document.getElementById('missing-wine-actions');
            const success = document.getElementById('missing-wine-success');
            if (actions) actions.style.display = 'none';
            if (success) success.style.display = 'block';
        }"""

assert target_missing_func in html, "target_missing_func not found in scanner.html"
html = html.replace(target_missing_func, replacement_missing_func, 1)

# 1.5 Update origPhotoBtn display check in scanner.html openWineDetail
target_orig_btn = """            if (origPhotoBtn) {
                const origImg = document.getElementById('original-img');
                const hasPhoto = (origImg && origImg.src && origImg.src.length > 5 && !origImg.src.endsWith('/'));
                origPhotoBtn.style.display = (source === 'scanner' && hasPhoto) ? 'inline-flex' : 'none';
            }"""

replacement_orig_btn = """            if (origPhotoBtn) {
                const hasPhoto = !!(window.currentUploadedImageURL || window.lastScannedPhotoDataUrl || sessionStorage.getItem('vina_last_scanned_photo'));
                origPhotoBtn.style.display = (source === 'scanner' || hasPhoto) ? 'inline-flex' : 'none';
            }"""

assert target_orig_btn in html, "target_orig_btn not found in scanner.html"
html = html.replace(target_orig_btn, replacement_orig_btn, 1)

with open("static/scanner.html", "w", encoding="utf-8") as f:
    f.write(html)
print("SUCCESS: scanner.html patched!")


# -------------------------------------------------------------
# 2. PATCH static/scanner.js
# -------------------------------------------------------------
with open("static/scanner.js", "r", encoding="utf-8") as f:
    js = f.read()

# 2.1 Update processImageFile in scanner.js
target_proc = """    async function processImageFile(file) {
        if (!file) return;

        if (typeof window.switchHubTab === 'function') {
            window.switchHubTab('scanner');
        }
        showView(scannerView);
        
        if (currentUploadedImageURL) {
            URL.revokeObjectURL(currentUploadedImageURL);
        }
        currentUploadedImageURL = URL.createObjectURL(file);
        
        if (scanningLine) scanningLine.classList.remove('hidden');
        
        setTimeout(async () => {
            showView(loadingView);
            
            try {
                const formData = new FormData();
                formData.append('image', file, 'snapshot.jpg');
                
                const predictEndpoint = apiUrl('/v1/eval/predict');
                const res = await fetch(predictEndpoint, {
                    method: 'POST',
                    body: formData
                });
                
                if (!res.ok) throw new Error(`Ошибка сервера: ${res.status}`);
                const data = await res.json();
                
                if (data.slug) {
                    const conf = data.confidence !== undefined ? data.confidence : data.score;
                    if (typeof window.setConfidence === 'function' && conf !== undefined && conf !== null) {
                        window.setConfidence(conf);
                    }
                    window.lastScannedSlug = data.slug;
                    if (typeof window.openWineDetail === 'function') {
                        window.openWineDetail(data.slug, 'scanner');
                    } else {
                        await loadWineCard(data.slug);
                        showView(resultView);
                    }
                } else if (data.status === 'not_in_catalog' || (data.confidence_percent !== undefined && data.confidence_percent < 50.0)) {
                    showView(scannerView);
                    const msg = data.message || data.user_message || 'Данного вина пока нет в каталоге, скоро появится, спасибо за проявленный интерес.';
                    showMissingWineModal(msg);
                } else {
                    showView(scannerView);
                    showMissingWineModal('Данного вина пока нет в каталоге, скоро появится, спасибо за проявленный интерес.');
                }
            } catch (error) {
                console.error(error);
                showToast('Ошибка при связи с сервером инференса.');
                showView(scannerView);
            } finally {
                if (scanningLine) scanningLine.classList.add('hidden');
                if (fileInput) fileInput.value = '';
            }
        }, 1200);
    }"""

replacement_proc = """    async function processImageFile(file) {
        if (!file) return;

        if (typeof window.switchHubTab === 'function') {
            window.switchHubTab('scanner');
        }
        showView(scannerView);
        
        // Читаем фото в Data URL для гарантированного сохранения в сессии
        const reader = new FileReader();
        reader.onload = function(e) {
            const dataUrl = e.target.result;
            currentUploadedImageURL = dataUrl;
            window.currentUploadedImageURL = dataUrl;
            window.lastScannedPhotoDataUrl = dataUrl;
            try {
                sessionStorage.setItem('vina_last_scanned_photo', dataUrl);
            } catch (err) {
                console.warn('Storage limit for photo:', err);
            }
            
            // Сразу выставляем фото во все элементы отображения
            const origImg = document.getElementById('original-img');
            if (origImg) origImg.src = dataUrl;
            const missingPhoto = document.getElementById('missing-wine-photo-preview');
            if (missingPhoto) missingPhoto.src = dataUrl;
        };
        reader.readAsDataURL(file);
        
        if (scanningLine) scanningLine.classList.remove('hidden');
        
        setTimeout(async () => {
            showView(loadingView);
            
            try {
                const formData = new FormData();
                formData.append('image', file, 'snapshot.jpg');
                
                const predictEndpoint = apiUrl('/v1/eval/predict');
                const res = await fetch(predictEndpoint, {
                    method: 'POST',
                    body: formData
                });
                
                if (!res.ok) throw new Error(`Ошибка сервера: ${res.status}`);
                const data = await res.json();
                
                // Сохраняем метаданные для отправки недостающего вина разработчикам
                window.lastMissingReqId = data.req_id || null;
                window.lastScannedOcrText = data.ocr_text || '';

                if (data.slug) {
                    const conf = data.confidence !== undefined ? data.confidence : data.score;
                    if (typeof window.setConfidence === 'function' && conf !== undefined && conf !== null) {
                        window.setConfidence(conf);
                    }
                    window.lastScannedSlug = data.slug;

                    // Гарантируем, что перед переходом в карточку вина фото зафиксировано
                    const origImg = document.getElementById('original-img');
                    if (origImg && (window.currentUploadedImageURL || window.lastScannedPhotoDataUrl)) {
                        origImg.src = window.currentUploadedImageURL || window.lastScannedPhotoDataUrl;
                    }
                    const origPhotoBtn = document.getElementById('btn-detail-original-photo');
                    if (origPhotoBtn) {
                        origPhotoBtn.style.display = 'inline-flex';
                    }

                    if (typeof window.openWineDetail === 'function') {
                        window.openWineDetail(data.slug, 'scanner');
                    } else {
                        await loadWineCard(data.slug);
                        showView(resultView);
                    }
                } else {
                    // Вино не найдено в базе — показываем снятое фото с уведомлением
                    showView(scannerView);
                    if (typeof window.showMissingWineModal === 'function') {
                        window.showMissingWineModal(data.message);
                    } else {
                        showMissingWineModal(data.message);
                    }
                }
            } catch (error) {
                console.error(error);
                showToast('Ошибка при связи с сервером инференса.');
                showView(scannerView);
            } finally {
                if (scanningLine) scanningLine.classList.add('hidden');
                if (fileInput) fileInput.value = '';
            }
        }, 1200);
    }"""

assert target_proc in js, "target_proc not found in scanner.js"
js = js.replace(target_proc, replacement_proc, 1)

# 2.2 Update openWineDetail in scanner.js
target_js_btn = """        if (origPhotoBtn) {
            const origImg = document.getElementById('original-img');
            const hasPhoto = (origImg && origImg.src && origImg.src.length > 5 && !origImg.src.endsWith('/'));
            origPhotoBtn.style.display = (source === 'scanner' && hasPhoto) ? 'inline-flex' : 'none';
        }"""

replacement_js_btn = """        if (origPhotoBtn) {
            const hasPhoto = !!(window.currentUploadedImageURL || window.lastScannedPhotoDataUrl || sessionStorage.getItem('vina_last_scanned_photo'));
            origPhotoBtn.style.display = (source === 'scanner' || hasPhoto) ? 'inline-flex' : 'none';
        }"""

assert target_js_btn in js, "target_js_btn not found in scanner.js"
js = js.replace(target_js_btn, replacement_js_btn, 1)

with open("static/scanner.js", "w", encoding="utf-8") as f:
    f.write(js)
print("SUCCESS: scanner.js patched!")
