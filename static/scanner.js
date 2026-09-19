document.addEventListener('DOMContentLoaded', () => {
    // --- API Configuration & Bridge Support ---
    function getApiBase() {
        const urlParams = new URLSearchParams(window.location.search);
        const apiParam = urlParams.get('api');
        if (apiParam) {
            const clean = apiParam.trim().replace(/\/+$/, '');
            localStorage.setItem('vina_api_url', clean);
            return clean;
        }

        // Always prefer direct local connection if running locally
        const isLocalHost = window.location.hostname === 'localhost' || 
                            window.location.hostname === '127.0.0.1' || 
                            window.location.hostname === '0.0.0.0' ||
                            window.location.port === '8080' ||
                            !window.location.hostname;
        if (isLocalHost) {
            return '';
        }

        const saved = localStorage.getItem('vina_api_url');
        if (saved) {
            return saved.trim().replace(/\/+$/, '');
        }
        return '';
    }

    function apiUrl(path) {
        const base = getApiBase();
        if (!path.startsWith('/')) path = '/' + path;
        return base ? `${base}${path}` : path;
    }

    // --- DOM Elements ---
    const fileInput = document.getElementById('file-input');
    const scannerView = document.getElementById('scanner-view');
    const loadingView = document.getElementById('loading-view');
    const resultView = document.getElementById('result-view');
    const btnBack = document.getElementById('btn-back');
    const scanningLine = document.querySelector('.scanning-line');
    
    // Status & Settings Elements
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.getElementById('status-text');
    const btnSettings = document.getElementById('btn-settings');
    const settingsModal = document.getElementById('settings-modal');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const modalBackdrop = document.querySelector('.modal-backdrop');
    const inputApiUrl = document.getElementById('input-api-url');
    const btnTestConnection = document.getElementById('btn-test-connection');
    const btnSaveSettings = document.getElementById('btn-save-settings');
    const feedbackBox = document.getElementById('connection-feedback');

    // Result View Elements
    const imgWine = document.getElementById('wine-image');
    const elWinery = document.getElementById('wine-winery');
    const elTitle = document.getElementById('wine-title');
    const elColor = document.getElementById('wine-color');
    const elCategory = document.getElementById('wine-category');
    const elRegion = document.getElementById('wine-region');
    const elGrape = document.getElementById('wine-grape');
    const elDesc = document.getElementById('wine-description');
    const btnShowOriginal = document.getElementById('btn-show-original');

    // Original View Elements
    const originalView = document.getElementById('original-view');
    const originalImg = document.getElementById('original-img');
    const originalCanvas = document.getElementById('original-canvas');
    const btnBackToResult = document.getElementById('btn-back-to-result');
    const btnAddToDb = document.getElementById('btn-add-to-db');

    let currentUploadedImageURL = null;

    // --- Views Switcher ---
    function showView(view) {
        [scannerView, loadingView, resultView, originalView].forEach(v => {
            if (v) v.classList.remove('active');
        });
        if (view) view.classList.add('active');
    }

    // --- Health Check & Status Monitor ---
    async function checkServerHealth(customUrl = null) {
        const targetUrl = customUrl !== null ? (customUrl ? `${customUrl.replace(/\/+$/, '')}/api/health` : '/api/health') : apiUrl('/api/health');
        
        statusDot.className = 'status-dot';
        statusText.textContent = 'Проверка...';

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            const res = await fetch(targetUrl, { signal: controller.signal });
            clearTimeout(timeoutId);

            if (res.ok) {
                const data = await res.json();
                statusDot.className = 'status-dot online';
                statusText.textContent = data.gpu_available ? 'RTX 3090' : 'Онлайн';
                return { ok: true, data };
            } else {
                throw new Error(`HTTP ${res.status}`);
            }
        } catch (e) {
            statusDot.className = 'status-dot offline';
            statusText.textContent = 'Офлайн';
            return { ok: false, error: e.message };
        }
    }

    // Run health check initially
    checkServerHealth();

    // --- Settings Modal Handlers ---
    function openSettings() {
        inputApiUrl.value = localStorage.getItem('vina_api_url') || '';
        feedbackBox.className = 'feedback-box hidden';
        settingsModal.classList.remove('hidden');
    }

    function closeSettings() {
        settingsModal.classList.add('hidden');
    }

    function showFeedback(text, type) {
        feedbackBox.textContent = text;
        feedbackBox.className = `feedback-box ${type}`;
    }

    btnSettings.addEventListener('click', openSettings);
    btnCloseModal.addEventListener('click', closeSettings);
    modalBackdrop.addEventListener('click', closeSettings);

    const btnResetLocal = document.getElementById('btn-reset-local');
    if (btnResetLocal) {
        btnResetLocal.addEventListener('click', async () => {
            localStorage.removeItem('vina_api_url');
            inputApiUrl.value = '';
            closeSettings();
            await checkServerHealth();
        });
    }

    btnTestConnection.addEventListener('click', async () => {
        const testUrl = inputApiUrl.value.trim();
        showFeedback('Проверка соединения...', '');
        const res = await checkServerHealth(testUrl);
        if (res.ok) {
            showFeedback(`Успешно! Сервер доступен (${res.data.gpu_name || 'OK'}).`, 'success');
        } else {
            showFeedback('Не удалось связаться с сервером. Проверьте запущен ли cloudflared туннель.', 'error');
        }
    });

    btnSaveSettings.addEventListener('click', async () => {
        const val = inputApiUrl.value.trim().replace(/\/+$/, '');
        if (val) {
            localStorage.setItem('vina_api_url', val);
        } else {
            localStorage.removeItem('vina_api_url');
        }
        await checkServerHealth();
        closeSettings();
    });

    // --- File Upload & Scan Logic ---
    fileInput.addEventListener('change', async (e) => {
        if (!e.target.files.length) return;
        
        const file = e.target.files[0];
        if (currentUploadedImageURL) {
            URL.revokeObjectURL(currentUploadedImageURL);
        }
        currentUploadedImageURL = URL.createObjectURL(file);
        
        scanningLine.classList.remove('hidden');
        
        setTimeout(async () => {
            showView(loadingView);
            
            try {
                const formData = new FormData();
                formData.append('image', file);
                
                const predictEndpoint = apiUrl('/v1/eval/predict');
                const res = await fetch(predictEndpoint, {
                    method: 'POST',
                    body: formData
                });
                
                if (!res.ok) throw new Error(`Ошибка сервера: ${res.status}`);
                const data = await res.json();
                
                if (data.slug) {
                    await loadWineCard(data.slug);
                    showView(resultView);
                } else {
                    alert('Вино не найдено в каталоге. Попробуйте другой ракурс.');
                    showView(scannerView);
                }
            } catch (error) {
                console.error(error);
                alert('Ошибка при связи с сервером. Проверьте настройки туннеля (⚙️).');
                showView(scannerView);
            } finally {
                scanningLine.classList.add('hidden');
                fileInput.value = '';
            }
        }, 1200);
    });

    // --- Load Wine Metadata & Image ---
    async function loadWineCard(slug) {
        const res = await fetch(apiUrl(`/api/wine/${slug}`));
        if (!res.ok) throw new Error('Карточка не найдена');
        const wine = await res.json();
        
        // Image URL through API bridge
        imgWine.src = apiUrl(`/api/image/${slug}`);
        imgWine.onerror = () => { imgWine.src = 'https://via.placeholder.com/300x500?text=Wine'; };
        
        elWinery.textContent = wine.winery || '';
        elTitle.textContent = wine.name || slug;
        elColor.textContent = wine.color || '';
        elCategory.textContent = wine.category || '';
        elRegion.textContent = wine.region || '';
        elGrape.textContent = wine.grape || '';
        elDesc.textContent = wine.description || '';
    }

    btnBack.addEventListener('click', () => {
        showView(scannerView);
    });

    if (btnShowOriginal) {
        btnShowOriginal.addEventListener('click', () => {
            if (currentUploadedImageURL) {
                originalImg.src = currentUploadedImageURL;
                resetOriginalTransform();
                showView(originalView);
            } else {
                alert("Исходное фото не найдено");
            }
        });
    }

    if (btnBackToResult) {
        btnBackToResult.addEventListener('click', () => {
            showView(resultView);
        });
    }

    if (btnAddToDb) {
        btnAddToDb.addEventListener('click', () => {
            alert("Функция 'Добавить в базу' в разработке");
        });
    }

    // Pairing buttons
    document.querySelectorAll('.btn-pairing').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-pairing').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        });
    });

    // ==========================================
    // Original Photo Zoom & Pan Logic
    // ==========================================
    let origScale = 1;
    let origPosX = 0;
    let origPosY = 0;
    let origIsDragging = false;
    let origStartX, origStartY;

    function updateOriginalTransform() {
        if (originalImg) originalImg.style.transform = `translate(${origPosX}px, ${origPosY}px) scale(${origScale})`;
    }

    function resetOriginalTransform() {
        origScale = 1;
        origPosX = 0;
        origPosY = 0;
        updateOriginalTransform();
    }

    if (originalCanvas) {
        originalCanvas.addEventListener("wheel", (e) => {
            e.preventDefault();
            const zoomFactor = 1.1;
            if (e.deltaY < 0) {
                origScale *= zoomFactor;
            } else {
                origScale /= zoomFactor;
            }
            updateOriginalTransform();
        }, { passive: false });

        // Pan desktop
        originalCanvas.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return; 
            origIsDragging = true;
            origStartX = e.clientX - origPosX;
            origStartY = e.clientY - origPosY;
        });

        window.addEventListener("mousemove", (e) => {
            if (!origIsDragging) return;
            origPosX = e.clientX - origStartX;
            origPosY = e.clientY - origStartY;
            updateOriginalTransform();
        });

        window.addEventListener("mouseup", () => {
            origIsDragging = false;
        });

        // Pan + Pinch mobile
        let origInitDist = null;
        let origInitScale = 1;

        originalCanvas.addEventListener("touchstart", (e) => {
            if (e.touches.length === 1) {
                origIsDragging = true;
                origStartX = e.touches[0].clientX - origPosX;
                origStartY = e.touches[0].clientY - origPosY;
            } else if (e.touches.length === 2) {
                origIsDragging = false;
                const t1 = e.touches[0];
                const t2 = e.touches[1];
                origInitDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
                origInitScale = origScale;
            }
        });

        window.addEventListener("touchmove", (e) => {
            if (originalView && !originalView.classList.contains("active")) return;
            
            if (e.touches.length === 1 && origIsDragging) {
                origPosX = e.touches[0].clientX - origStartX;
                origPosY = e.touches[0].clientY - origStartY;
                updateOriginalTransform();
            } else if (e.touches.length === 2 && origInitDist) {
                const t1 = e.touches[0];
                const t2 = e.touches[1];
                const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
                origScale = origInitScale * (dist / origInitDist);
                updateOriginalTransform();
            }
        });

        window.addEventListener("touchend", (e) => {
            if (e.touches.length < 2) origInitDist = null;
            if (e.touches.length === 0) origIsDragging = false;
        });
    }

    // ==========================================
    // Lightbox Zoom & Pan Logic (Scanner Result)
    // ==========================================
    const lightboxModal = document.getElementById("lightbox-modal");
    const lightboxImg = document.getElementById("lightbox-img");
    const lightboxCanvas = document.getElementById("lightbox-canvas");
    const btnCloseLightbox = document.getElementById("btn-close-lightbox");
    const btnZoomIn = document.getElementById("btn-zoom-in");
    const btnZoomOut = document.getElementById("btn-zoom-out");
    const btnZoomReset = document.getElementById("btn-zoom-reset");
    const lightboxTitle = document.getElementById("lightbox-title");

    let scale = 1;
    let posX = 0;
    let posY = 0;
    let isDragging = false;
    let startX, startY;

    function updateTransform() {
        lightboxImg.style.transform = `translate(${posX}px, ${posY}px) scale(${scale})`;
        btnZoomReset.textContent = Math.round(scale * 100) + "%";
    }

    function resetTransform() {
        scale = 1;
        posX = 0;
        posY = 0;
        updateTransform();
    }

    function openLightbox(src, title) {
        if (!src || src === "") return;
        lightboxImg.src = src;
        lightboxTitle.textContent = title || "Просмотр скана";
        resetTransform();
        lightboxModal.classList.remove("hidden");
    }

    function closeLightbox() {
        lightboxModal.classList.add("hidden");
        lightboxImg.src = "";
    }

    // Attach to the result wine image
    if (imgWine) {
        imgWine.style.cursor = "zoom-in";
        // Both click and touchend to ensure it triggers on mobile
        const handleOpen = (e) => {
            if (e.type === 'touchend') e.preventDefault(); // prevent double firing
            openLightbox(imgWine.src, elTitle.textContent || "Этикетка вина");
        };
        imgWine.addEventListener("click", handleOpen);
        imgWine.addEventListener("touchend", handleOpen);
    }

    // Controls
    if(btnCloseLightbox) btnCloseLightbox.addEventListener("click", closeLightbox);
    if(btnZoomReset) btnZoomReset.addEventListener("click", resetTransform);
    
    if(btnZoomIn) {
        btnZoomIn.addEventListener("click", () => {
            scale *= 1.3;
            updateTransform();
        });
    }
    
    if(btnZoomOut) {
        btnZoomOut.addEventListener("click", () => {
            scale /= 1.3;
            updateTransform();
        });
    }

    // Mouse wheel zoom
    if (lightboxCanvas) {
        lightboxCanvas.addEventListener("wheel", (e) => {
            e.preventDefault();
            const zoomFactor = 1.1;
            if (e.deltaY < 0) {
                scale *= zoomFactor;
            } else {
                scale /= zoomFactor;
            }
            updateTransform();
        }, { passive: false });

        // Pan logic for desktop (mouse)
        lightboxCanvas.addEventListener("mousedown", (e) => {
            if (e.button !== 0) return; 
            isDragging = true;
            startX = e.clientX - posX;
            startY = e.clientY - posY;
        });

        window.addEventListener("mousemove", (e) => {
            if (!isDragging) return;
            posX = e.clientX - startX;
            posY = e.clientY - startY;
            updateTransform();
        });

        window.addEventListener("mouseup", () => {
            isDragging = false;
        });

        // Mobile touch logic (Pan + Pinch-to-Zoom)
        let initialDistance = null;
        let initialScale = 1;

        lightboxCanvas.addEventListener("touchstart", (e) => {
            if (e.touches.length === 1) {
                isDragging = true;
                startX = e.touches[0].clientX - posX;
                startY = e.touches[0].clientY - posY;
            } else if (e.touches.length === 2) {
                isDragging = false;
                const touch1 = e.touches[0];
                const touch2 = e.touches[1];
                initialDistance = Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY);
                initialScale = scale;
            }
        });

        window.addEventListener("touchmove", (e) => {
            if (e.touches.length === 1 && isDragging) {
                posX = e.touches[0].clientX - startX;
                posY = e.touches[0].clientY - startY;
                updateTransform();
            } else if (e.touches.length === 2 && initialDistance) {
                const touch1 = e.touches[0];
                const touch2 = e.touches[1];
                const currentDistance = Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY);
                const zoomDelta = currentDistance / initialDistance;
                scale = initialScale * zoomDelta;
                updateTransform();
            }
        });

        window.addEventListener("touchend", (e) => {
            if (e.touches.length < 2) {
                initialDistance = null;
            }
            if (e.touches.length === 0) {
                isDragging = false;
            }
        });
    }

    // Keyboard
    window.addEventListener("keydown", (e) => {
        if (!lightboxModal.classList.contains("hidden")) {
            if (e.key === "Escape") {
                closeLightbox();
            }
        }
    });

});
