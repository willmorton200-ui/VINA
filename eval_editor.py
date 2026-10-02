import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json
import pandas as pd
import os

app = FastAPI()

OWNER_EVAL_DIR = "D:/VINA/owner_eval"
CATALOG_IMAGES_DIR = "D:/VINA/wines_images_clean/wines_images"
CATALOG_CSV = "D:/VINA/wines_integrated_clean.csv"

app.mount("/owner_eval", StaticFiles(directory=OWNER_EVAL_DIR), name="owner_eval")
if os.path.exists(CATALOG_IMAGES_DIR):
    app.mount("/catalog_images", StaticFiles(directory=CATALOG_IMAGES_DIR), name="catalog_images")

catalog_df = pd.read_csv(CATALOG_CSV)
# Handle potential NaN values
catalog_df = catalog_df.fillna("")

CATALOG_LIST = []
for _, row in catalog_df.iterrows():
    CATALOG_LIST.append({
        "slug": row.get("Slug", ""),
        "name": row.get("Название вина", ""),
        "image": row.get("Файл в wines_images", "")
    })

@app.get("/")
async def get_index():
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>VINA Eval Editor</title>
        <style>
            body { font-family: sans-serif; background: #111; color: #fff; margin: 0; padding: 20px; }
            .container { max-width: 1400px; margin: 0 auto; }
            .case-card { display: flex; background: #222; margin-bottom: 20px; padding: 20px; border-radius: 8px; gap: 20px; }
            .image-col { flex: 0 0 300px; }
            .image-col img { max-width: 100%; max-height: 400px; object-fit: contain; border-radius: 4px; }
            .info-col { flex: 1; }
            .catalog-col { flex: 0 0 350px; max-height: 400px; overflow-y: auto; background: #333; padding: 10px; border-radius: 4px; }
            .selected-image-col { flex: 0 0 250px; text-align: center; }
            .selected-image-col img { max-width: 100%; max-height: 400px; object-fit: contain; border-radius: 4px; display: none; }
            .catalog-item { padding: 10px; cursor: pointer; border-bottom: 1px solid #444; display: flex; gap: 10px; }
            .catalog-item:hover { background: #444; }
            .catalog-item img { width: 40px; height: 40px; object-fit: cover; border-radius: 20px; }
            input[type="text"] { width: 100%; padding: 10px; margin-bottom: 10px; background: #222; color: #fff; border: 1px solid #555; }
            .current-expected { margin-top: 10px; padding: 10px; background: #1a4d1a; border-radius: 4px; }
            button { padding: 10px 20px; background: #4CAF50; color: white; border: none; cursor: pointer; border-radius: 4px; margin-top: 10px; }
            button:hover { background: #45a049; }
            .search-box { margin-bottom: 10px; }
            .saved-msg { color: #4CAF50; margin-left: 10px; display: none; }
            /* Modal styles */
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.9); overflow: auto; align-items: center; justify-content: center; }
            .modal-content { max-width: 90%; max-height: 90%; margin: auto; display: block; object-fit: contain; }
            .modal-close { position: absolute; top: 15px; right: 35px; color: #f1f1f1; font-size: 40px; font-weight: bold; cursor: pointer; }
            .modal-close:hover { color: #bbb; }
            .zoomable { cursor: zoom-in; transition: 0.3s; }
            .zoomable:hover { opacity: 0.8; }
        </style>
    </head>
    <body>
        <!-- Image Modal -->
        <div id="image-modal" class="modal" onclick="closeModal(event)">
            <span class="modal-close" onclick="closeModal(event)">&times;</span>
            <img class="modal-content" id="modal-img">
        </div>
        
        <div class="container">
            <h1 id="editor-title">Редактор owner_eval/119</h1>
            <div style="margin-bottom: 20px;">
                <label style="font-size: 1.2em; margin-right: 10px;">Выбор датасета:</label>
                <select id="dataset-select" onchange="changeDataset()" style="padding: 8px; font-size: 1.1em; background: #222; color: #fff; border: 1px solid #555; border-radius: 4px;">
                    <option value="119">119</option>
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                </select>
            </div>
            <div id="cases-container">Загрузка...</div>
        </div>
        
        <script>
            function openModal(src) {
                const modal = document.getElementById("image-modal");
                const modalImg = document.getElementById("modal-img");
                modal.style.display = "flex";
                modalImg.src = src;
            }
            function closeModal(e) {
                if (e.target.id === "image-modal" || e.target.className === "modal-close") {
                    document.getElementById("image-modal").style.display = "none";
                }
            }

            let cases = [];
            let catalog = [];
            let currentDataset = "119";
            
            function changeDataset() {
                currentDataset = document.getElementById("dataset-select").value;
                document.getElementById("editor-title").innerText = `Редактор owner_eval/${currentDataset}`;
                loadCases();
            }
            
            async function loadData() {
                const catalogRes = await fetch('/api/catalog');
                catalog = await catalogRes.json();
                
                await loadCases();
            }
            
            async function loadCases() {
                const casesRes = await fetch(`/api/cases?dataset=${currentDataset}`);
                cases = await casesRes.json();
                renderCases();
            }
            
            function renderCases() {
                const container = document.getElementById('cases-container');
                container.innerHTML = '';
                
                cases.forEach((c, index) => {
                    const card = document.createElement('div');
                    card.className = 'case-card';
                    card.id = `case-${c.query_id}`;
                    
                    const expectedWine = catalog.find(w => w.slug === c.expected_slug);
                    
                    card.innerHTML = `
                        <div class="image-col">
                            <h3>${c.query_id}</h3>
                            <img class="zoomable" src="/owner_eval/${currentDataset}/queries/${c.image_path}" alt="Query Image" onclick="openModal(this.src)">
                        </div>
                        <div class="info-col">
                            <div class="current-expected">
                                <strong>Ожидаемый Slug:</strong> <span id="slug-${c.query_id}">${c.expected_slug}</span><br>
                                <strong>Название:</strong> <span id="name-${c.query_id}">${expectedWine ? expectedWine.name : 'НЕ НАЙДЕНО'}</span>
                            </div>
                            <button onclick="saveCase('${c.query_id}')">Сохранить этот Slug</button>
                            <button style="background: #e74c3c; margin-left: 10px;" onclick="deleteCase('${c.query_id}')">Удалить из теста</button>
                            <span class="saved-msg" id="msg-${c.query_id}">Сохранено!</span>
                        </div>
                        <div class="catalog-col">
                            <input type="text" class="search-box" placeholder="Поиск по названию или slug..." onkeyup="filterCatalog('${c.query_id}', this.value)">
                            <div id="catalog-list-${c.query_id}"></div>
                        </div>
                        <div class="selected-image-col">
                            <img class="zoomable" id="preview-${c.query_id}" src="${expectedWine ? '/catalog_images/' + expectedWine.image : ''}" 
                                 style="display: ${expectedWine && expectedWine.image ? 'block' : 'none'};" 
                                 onerror="this.style.display='none'" onclick="openModal(this.src)">
                        </div>
                    `;
                    
                    container.appendChild(card);
                    filterCatalog(c.query_id, "");
                });
            }
            
            function filterCatalog(queryId, searchStr) {
                const listDiv = document.getElementById(`catalog-list-${queryId}`);
                listDiv.innerHTML = '';
                
                searchStr = searchStr.toLowerCase();
                const filtered = catalog.filter(w => w.name.toLowerCase().includes(searchStr) || w.slug.toLowerCase().includes(searchStr)).slice(0, 30);
                
                filtered.forEach(w => {
                    const div = document.createElement('div');
                    div.className = 'catalog-item';
                    div.onclick = () => selectWine(queryId, w);
                    div.innerHTML = `
                        <img src="/catalog_images/${w.image}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAiIGhlaWdodD0iMTAwIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjNDQ0Ii8+PC9zdmc+'">
                        <div>
                            <strong>${w.name}</strong><br>
                            <small>${w.slug}</small>
                        </div>
                    `;
                    listDiv.appendChild(div);
                });
            }
            
            function selectWine(queryId, wine) {
                document.getElementById(`slug-${queryId}`).innerText = wine.slug;
                document.getElementById(`name-${queryId}`).innerText = wine.name;
                
                const previewImg = document.getElementById(`preview-${queryId}`);
                if (wine.image) {
                    previewImg.src = `/catalog_images/${wine.image}`;
                    previewImg.style.display = 'block';
                } else {
                    previewImg.style.display = 'none';
                }
                
                const caseIndex = cases.findIndex(c => c.query_id === queryId);
                if (caseIndex !== -1) {
                    cases[caseIndex].expected_slug = wine.slug;
                }
            }
            
            async function saveCase(queryId) {
                const c = cases.find(c => c.query_id === queryId);
                const res = await fetch('/api/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query_id: c.query_id, expected_slug: c.expected_slug, dataset: currentDataset })
                });
                if (res.ok) {
                    const msg = document.getElementById(`msg-${queryId}`);
                    msg.style.display = 'inline';
                    setTimeout(() => msg.style.display = 'none', 2000);
                }
            }
            
            async function deleteCase(queryId) {
                if (!confirm("Удалить эту картинку из тестового набора?")) return;
                
                const res = await fetch(`/api/delete?query_id=${queryId}&dataset=${currentDataset}`, { method: 'DELETE' });
                if (res.ok) {
                    const card = document.getElementById(`case-${queryId}`);
                    card.style.display = 'none';
                    cases = cases.filter(c => c.query_id !== queryId);
                }
            }
            
            loadData();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/catalog")
async def get_catalog():
    return JSONResponse(content=CATALOG_LIST)

@app.get("/api/cases")
async def get_cases(dataset: str = "119"):
    mapping_file = os.path.join(OWNER_EVAL_DIR, dataset, "mapping.json")
    if not os.path.exists(mapping_file):
        return JSONResponse(content=[])
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    return JSONResponse(content=mapping["cases"])

@app.post("/api/update")
async def update_case(request: Request):
    data = await request.json()
    q_id = data.get("query_id")
    expected_slug = data.get("expected_slug")
    dataset = data.get("dataset", "119")
    
    mapping_file = os.path.join(OWNER_EVAL_DIR, dataset, "mapping.json")
    
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        
    for c in mapping["cases"]:
        if c["query_id"] == q_id:
            c["expected_slug"] = expected_slug
            break
            
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        
    return {"status": "ok"}

@app.delete("/api/delete")
async def delete_case(query_id: str, dataset: str = "119"):
    mapping_file = os.path.join(OWNER_EVAL_DIR, dataset, "mapping.json")
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        
    mapping["cases"] = [c for c in mapping["cases"] if c["query_id"] != query_id]
    mapping["positive_count"] = len(mapping["cases"])
            
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)
