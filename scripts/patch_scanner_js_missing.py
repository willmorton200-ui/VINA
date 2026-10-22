# -*- coding: utf-8 -*-
with open("static/scanner.js", "r", encoding="utf-8") as f:
    content = f.read()

target = """    function showMissingWineModal(msg) {
        const modal = document.getElementById('missing-wine-modal');
        const msgEl = document.getElementById('missing-wine-message');
        if (msgEl && msg) msgEl.textContent = msg;
        if (modal) modal.style.display = 'flex';
    }

    window.closeMissingWineModal = function() {
        const modal = document.getElementById('missing-wine-modal');
        if (modal) modal.style.display = 'none';
    };"""

replacement = """    function showMissingWineModal(msg) {
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

    window.showMissingWineModal = showMissingWineModal;

    window.closeMissingWineModal = function() {
        const modal = document.getElementById('missing-wine-modal');
        if (modal) modal.style.display = 'none';
        if (typeof showView === 'function' && scannerView) {
            showView(scannerView);
        }
    };

    window.submitMissingWineToDevs = async function() {
        const btn = document.getElementById('btn-submit-missing-wine');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="somm-spinner" style="border-top-color:#fff;"></span> Отправка...';
        }
        const photoUrl = window.currentUploadedImageURL || window.lastScannedPhotoDataUrl || sessionStorage.getItem('vina_last_scanned_photo') || '';
        const reqId = window.lastMissingReqId || null;
        const ocr = window.lastScannedOcrText || '';

        try {
            await fetch(apiUrl('/api/missing-wines/report'), {
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
    };"""

assert target in content, "Target not found in static/scanner.js"
new_content = content.replace(target, replacement, 1)
with open("static/scanner.js", "w", encoding="utf-8") as f:
    f.write(new_content)
print("SUCCESS: static/scanner.js showMissingWineModal updated!")
