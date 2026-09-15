document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const scannerView = document.getElementById('scanner-view');
    const loadingView = document.getElementById('loading-view');
    const resultView = document.getElementById('result-view');
    const btnBack = document.getElementById('btn-back');
    const scanningLine = document.querySelector('.scanning-line');
    
    // UI Elements for result
    const imgWine = document.getElementById('wine-image');
    const elWinery = document.getElementById('wine-winery');
    const elTitle = document.getElementById('wine-title');
    const elColor = document.getElementById('wine-color');
    const elCategory = document.getElementById('wine-category');
    const elRegion = document.getElementById('wine-region');
    const elGrape = document.getElementById('wine-grape');
    const elDesc = document.getElementById('wine-description');

    function showView(view) {
        [scannerView, loadingView, resultView].forEach(v => v.classList.remove('active'));
        view.classList.add('active');
    }

    fileInput.addEventListener('change', async (e) => {
        if (!e.target.files.length) return;
        
        const file = e.target.files[0];
        scanningLine.classList.remove('hidden');
        
        // Show loading after a brief delay to show the scanning animation
        setTimeout(async () => {
            showView(loadingView);
            
            try {
                const formData = new FormData();
                formData.append('image', file);
                
                // Call predict endpoint
                const res = await fetch('/v1/eval/predict', {
                    method: 'POST',
                    body: formData
                });
                
                if (!res.ok) throw new Error('Ошибка сети');
                const data = await res.json();
                
                if (data.slug) {
                    await loadWineCard(data.slug);
                    showView(resultView);
                } else {
                    alert('Вино не найдено в каталоге. Попробуйте другое фото.');
                    showView(scannerView);
                }
            } catch (error) {
                console.error(error);
                alert('Произошла ошибка при распознавании.');
                showView(scannerView);
            } finally {
                scanningLine.classList.add('hidden');
                fileInput.value = ''; // Reset
            }
        }, 1500);
    });

    async function loadWineCard(slug) {
        const res = await fetch(`/api/wine/${slug}`);
        if (!res.ok) throw new Error('Карточка не найдена');
        const wine = await res.json();
        
        // Strapi uploads URL mapping
        const fileName = wine.image_path.split('\\').pop().split('/').pop();
        // Since we serve static files, we'll just mock the image or use a real path if we serve uploads
        // We'll use a placeholder for now since uploads folder is outside static.
        // Actually, let's create a route to serve uploads or use the test dataset
        
        // For now, let's just use a placeholder image if it fails
        imgWine.src = `/api/image/${slug}`; // We'll need to create this route!
        imgWine.onerror = () => { imgWine.src = 'https://via.placeholder.com/300x500?text=Wine'; };
        
        elWinery.textContent = wine.winery;
        elTitle.textContent = wine.name;
        elColor.textContent = wine.color;
        elCategory.textContent = wine.category;
        elRegion.textContent = wine.region;
        elGrape.textContent = wine.grape;
        elDesc.textContent = wine.description;
    }

    btnBack.addEventListener('click', () => {
        showView(scannerView);
    });

    // Pairing buttons interaction
    document.querySelectorAll('.btn-pairing').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.btn-pairing').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
        });
    });
});
