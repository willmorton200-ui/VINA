import os
import sys
import json

file_path = "D:/VINA/eval_editor.py"
with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# Update top level constants
code = code.replace(
    'MAPPING_FILE = "D:/VINA/owner_eval/119/mapping.json"\nQUERIES_DIR = "D:/VINA/owner_eval/119/queries"\n',
    'OWNER_EVAL_DIR = "D:/VINA/owner_eval"\n'
)

code = code.replace(
    'app.mount("/queries", StaticFiles(directory=QUERIES_DIR), name="queries")',
    'app.mount("/owner_eval", StaticFiles(directory=OWNER_EVAL_DIR), name="owner_eval")'
)

# HTML changes
code = code.replace(
    '<h1>Редактор owner_eval/119</h1>',
    '''<h1 id="editor-title">Редактор owner_eval/119</h1>
            <div style="margin-bottom: 20px;">
                <label style="font-size: 1.2em; margin-right: 10px;">Выбор датасета:</label>
                <select id="dataset-select" onchange="changeDataset()" style="padding: 8px; font-size: 1.1em; background: #222; color: #fff; border: 1px solid #555; border-radius: 4px;">
                    <option value="119">119</option>
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                </select>
            </div>'''
)

# JS variables
code = code.replace(
    'let cases = [];\n            let catalog = [];',
    'let cases = [];\n            let catalog = [];\n            let currentDataset = "119";\n            \n            function changeDataset() {\n                currentDataset = document.getElementById("dataset-select").value;\n                document.getElementById("editor-title").innerText = `Редактор owner_eval/${currentDataset}`;\n                loadCases();\n            }'
)

code = code.replace(
    '''async function loadData() {
                const catalogRes = await fetch('/api/catalog');
                catalog = await catalogRes.json();
                
                const casesRes = await fetch('/api/cases');
                cases = await casesRes.json();
                
                renderCases();
            }''',
    '''async function loadData() {
                const catalogRes = await fetch('/api/catalog');
                catalog = await catalogRes.json();
                
                await loadCases();
            }
            
            async function loadCases() {
                const casesRes = await fetch(`/api/cases?dataset=${currentDataset}`);
                cases = await casesRes.json();
                renderCases();
            }'''
)

code = code.replace(
    '<img src="/queries/${c.image_path}" alt="Query Image">',
    '<img src="/owner_eval/${currentDataset}/queries/${c.image_path}" alt="Query Image">'
)

code = code.replace(
    'body: JSON.stringify({ query_id: c.query_id, expected_slug: c.expected_slug })',
    'body: JSON.stringify({ query_id: c.query_id, expected_slug: c.expected_slug, dataset: currentDataset })'
)

code = code.replace(
    "const res = await fetch(`/api/delete?query_id=${queryId}`, { method: 'DELETE' });",
    "const res = await fetch(`/api/delete?query_id=${queryId}&dataset=${currentDataset}`, { method: 'DELETE' });"
)

# Update API
api_cases_old = '''@app.get("/api/cases")
async def get_cases():
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    return JSONResponse(content=mapping["cases"])'''

api_cases_new = '''@app.get("/api/cases")
async def get_cases(dataset: str = "119"):
    mapping_file = os.path.join(OWNER_EVAL_DIR, dataset, "mapping.json")
    if not os.path.exists(mapping_file):
        return JSONResponse(content=[])
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
    return JSONResponse(content=mapping["cases"])'''

code = code.replace(api_cases_old, api_cases_new)

api_update_old = '''@app.post("/api/update")
async def update_case(request: Request):
    data = await request.json()
    q_id = data.get("query_id")
    expected_slug = data.get("expected_slug")
    
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        
    for c in mapping["cases"]:
        if c["query_id"] == q_id:
            c["expected_slug"] = expected_slug
            break
            
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        
    return {"status": "ok"}'''

api_update_new = '''@app.post("/api/update")
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
        
    return {"status": "ok"}'''

code = code.replace(api_update_old, api_update_new)

api_del_old = '''@app.delete("/api/delete")
async def delete_case(query_id: str):
    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        
    mapping["cases"] = [c for c in mapping["cases"] if c["query_id"] != query_id]
    mapping["positive_count"] = len(mapping["cases"])
            
    with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        
    return {"status": "ok"}'''

api_del_new = '''@app.delete("/api/delete")
async def delete_case(query_id: str, dataset: str = "119"):
    mapping_file = os.path.join(OWNER_EVAL_DIR, dataset, "mapping.json")
    with open(mapping_file, 'r', encoding='utf-8') as f:
        mapping = json.load(f)
        
    mapping["cases"] = [c for c in mapping["cases"] if c["query_id"] != query_id]
    mapping["positive_count"] = len(mapping["cases"])
            
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
        
    return {"status": "ok"}'''

code = code.replace(api_del_old, api_del_new)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code)

print("done")
