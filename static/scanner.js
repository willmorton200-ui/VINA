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

    // --- Views Switcher ---
    function showView(view) {
        [scannerView, loadingView, resultView].forEach(v => v.classList.remove('active'));
        view.classList.add('active');
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

    // Pairing buttons
    document.querySelectorAll('.btn-pairing').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-pairing').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        });
    });
});
