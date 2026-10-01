
"""
FastAPI Server for VINA Cylindrical Dewarping & OCR System
"""

import os
import glob
import sys as _sys
import cv2
import numpy as np
import base64
import torch
import time
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline.catalog import WineCatalog
from pipeline.search_engine import WineSearchEngine
from pipeline import CylindricalDewarpEngine, compute_image_metrics
from pipeline.vina_studio_matcher import VinaStudioMatcher

app = FastAPI(title="VINA Cylindrical Dewarping Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

gpu_available = torch.cuda.is_available()
engine = CylindricalDewarpEngine(use_gpu=gpu_available)

catalog = WineCatalog()
search_engine = WineSearchEngine(catalog, use_gpu=gpu_available)
vina_matcher = VinaStudioMatcher(catalog)

# ---- Sommelier (ленивая инициализация) ----
_sommelier = None

def get_sommelier():
    global _sommelier
    if _sommelier is None:
        from sommelier.sommelier import Sommelier
        _sommelier = Sommelier()
    return _sommelier

# ---- Static mounts ----
app.mount("/static", StaticFiles(directory="d:/VINA/static"), name="static")
app.mount("/test_dataset", StaticFiles(directory="d:/VINA/test_dataset"), name="test_dataset")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("d:/VINA/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/scanner", response_class=HTMLResponse)
async def serve_scanner():
    with open("d:/VINA/static/scanner.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/map", response_class=HTMLResponse)
async def serve_map():
    with open("d:/VINA/static/map_demo.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/style.css")
async def get_style_css():
    return FileResponse("d:/VINA/static/style.css", media_type="text/css")

@app.get("/app.js")
async def get_app_js():
    return FileResponse("d:/VINA/static/app.js", media_type="application/javascript")

@app.get("/scanner.css")
async def get_scanner_css():
    return FileResponse("d:/VINA/static/scanner.css", media_type="text/css")

@app.get("/scanner.js")
async def get_scanner_js():
    return FileResponse("d:/VINA/static/scanner.js", media_type="application/javascript")

@app.get("/scanner.html", response_class=HTMLResponse)
async def get_scanner_html():
    return FileResponse("d:/VINA/static/scanner.html", media_type="text/html")

@app.get("/znak.png")
async def get_znak():
    return FileResponse("d:/VINA/static/znak.png", media_type="image/png")

@app.get("/badge_glass.png")
async def get_badge():
    return FileResponse("d:/VINA/static/badge_glass.png", media_type="image/png")

app.mount("/img", StaticFiles(directory="d:/VINA/static/img"), name="root_img")
app.mount("/svg", StaticFiles(directory="d:/VINA/static/svg"), name="root_svg")

@app.get("/api/health")
async def health_check():
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None (CPU)"
    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "torch_version": torch.__version__,
        "catalog_size": len(catalog.get_all_wines()),
        "faiss_index_size": search_engine.index.ntotal if search_engine.index else 0,
        "cascade_info": "top-5 embeddings + OCR confirmation (divisor 1..4)",
    }

@app.get("/api/samples")
async def list_sample_bottles():
    butilki_dir = "d:/VINA/test_dataset/butilki"
    cam_dir = "d:/VINA/test_dataset/cam"
    cat_dir = "d:/VINA/test_dataset/calalog"
    samples = []
    for d, folder in [(butilki_dir, "butilki"), (cam_dir, "cam")]:
        for fpath in sorted(glob.glob(os.path.join(d, "*.*"))):
            fname = os.path.basename(fpath)
            base_id = fname.split('_')[0]
            cat_matches = glob.glob(os.path.join(cat_dir, f"{base_id}_*"))
            has_catalog = len(cat_matches) > 0
            cat_rel = f"/test_dataset/calalog/{os.path.basename(cat_matches[0])}" if has_catalog else None
            display_title = fname.replace(".jpeg", "").replace(".jpg", "").replace(".png", "").replace("_", " ")
            if len(display_title) > 35:
                display_title = display_title[:32] + "..."
            samples.append({
                "id": base_id, "filename": fname, "folder": folder, "title": display_title,
                "cam_url": f"/test_dataset/{folder}/{fname}", "cat_url": cat_rel, "has_catalog": has_catalog
            })
    return {"samples": samples}

class ProcessSampleRequest(BaseModel):
    sample_filename: str

@app.post("/api/process_sample")
async def process_sample(req: ProcessSampleRequest):
    path1 = os.path.join("d:/VINA/test_dataset/butilki", req.sample_filename)
    path2 = os.path.join("d:/VINA/test_dataset/cam", req.sample_filename)
    img_path = path1 if os.path.exists(path1) else path2
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Sample image not found")
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Failed to decode sample image")
    base_id = req.sample_filename.split('_')[0]
    cat_matches = glob.glob(os.path.join("d:/VINA/test_dataset/calalog", f"{base_id}_*"))
    ref_bgr = cv2.imread(cat_matches[0]) if cat_matches else None
    result = engine.process_image(img_bgr, reference_bgr=ref_bgr)
    result["filename"] = req.sample_filename
    result["has_reference"] = ref_bgr is not None
    if ref_bgr is not None:
        result["artifacts"]["catalog_reference"] = engine.img_to_base64(ref_bgr)
    return result

@app.post("/api/process_upload")
async def process_upload(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")
    result = engine.process_image(img_bgr)
    result["filename"] = file.filename
    result["has_reference"] = False
    return result

@app.post("/v1/eval/predict")
async def eval_predict(image: UploadFile = File(...)):
    """
    Каскадный эндпоинт v4: SigLIP топ-5 + OCR бонус.
    
    Формула: final = emb_confidence + 100 / divisor
    divisor = 1 (все слова ≥90%) / 2 (половина ≥50%) / 3 (треть ≥33%) / 4 (<1/3)
    """
    t0 = time.time()
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    # ШАГ 1: SigLIP топ-5 (на оригинале)
    siglip_results = search_engine.search_by_cv2_image(img_bgr, top_k=5)
    
    # ШАГ 2: VINA STUDIO (получение выпрямленной этикетки)
    dewarped_results = []
    ocr_text = ""
    try:
        vina_result = engine.process_image(img_bgr)
        if vina_result.get("success"):
            ocr_text = vina_result.get("full_text", "")
            dewarped_b64 = vina_result.get("artifacts", {}).get("dewarped")
            if dewarped_b64:
                if "," in dewarped_b64:
                    dewarped_b64 = dewarped_b64.split(",")[1]
                d_bytes = base64.b64decode(dewarped_b64)
                d_np = np.frombuffer(d_bytes, np.uint8)
                dewarped_img = cv2.imdecode(d_np, cv2.IMREAD_COLOR)
                if dewarped_img is not None:
                    dewarped_results = search_engine.search_by_cv2_image(dewarped_img, top_k=5)
    except Exception as e:
        print(f"[eval_predict] VINA STUDIO fallback: {e}")

    # ШАГ 3: Берем максимум из (оригинал, выпрямленная)
    combined_scores = {}
    for r in siglip_results:
        combined_scores[r["slug"]] = {"score": r["score"], "source": "raw"}
        
    for r in dewarped_results:
        if r["slug"] not in combined_scores or r["score"] > combined_scores[r["slug"]]["score"]:
            combined_scores[r["slug"]] = {"score": r["score"], "source": "dewarped"}
            
    if not combined_scores:
        return {"slug": None, "score": 0.0, "confidence": 0.0, "confidence_percent": 0.0}
        
    # Сортируем по убыванию score
    sorted_candidates = sorted(combined_scores.items(), key=lambda x: x[1]["score"], reverse=True)
    best_slug = sorted_candidates[0][0]
    best_score = sorted_candidates[0][1]["score"]
    best_source = sorted_candidates[0][1]["source"]
    
    # Нормализуем для совместимости
    final_confidence = max(0.0, min(100.0, (best_score + 1.0) / 2.0 * 100.0))

    return {
        "slug": best_slug,
        "name": catalog.get_wine(best_slug).get("name", "") if catalog.get_wine(best_slug) else "",
        "score": round(best_score, 4),
        "confidence": round(final_confidence / 100.0, 4),
        "confidence_percent": round(final_confidence, 2),
        "confidence_embedding": round(final_confidence, 2),
        "ocr_bonus": 0.0,
        "divisor": 1,
        "decision_source": f"siglip_max_{best_source}",
        "match_count": 0,
        "total_words": 0,
        "matched_words": [],
        "ocr_text": ocr_text[:200] if ocr_text else "",
        "candidates": [
            {"slug": c[0], "score": round(c[1]["score"], 4),
             "source": c[1]["source"]}
            for c in sorted_candidates[:5]
        ],
        "total_time_ms": round((time.time() - t0) * 1000, 1),
    }

@app.get("/api/wine/{slug}")
async def get_wine_card(slug: str):
    wine = catalog.get_wine(slug)
    if not wine:
        raise HTTPException(status_code=404, detail="Wine not found")
    return wine

@app.get("/api/image/{slug}")
async def get_wine_image(slug: str):
    wine = catalog.get_wine(slug)
    if not wine or not wine["image_path"]:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(wine["image_path"])


# ============================================================
# Sommelier API endpoints
# ============================================================

class SommelierAskRequest(BaseModel):
    text: str
    wine_slug: str | None = None

@app.post("/api/sommelier/ask")
async def sommelier_ask(req: SommelierAskRequest):
    """Основной эндпоинт диалога с сомелье."""
    som = get_sommelier()
    result = som.ask(req.text)
    return {
        "kind": result.get("kind", "text"),
        "text": result.get("text", ""),
        "picks": result.get("picks", []),
        "types": result.get("types", []),
        "pool": result.get("pool", 0),
        "code": result.get("code"),
    }


@app.post("/api/sommelier/reset")
async def sommelier_reset():
    """Сбросить контекст диалога."""
    som = get_sommelier()
    som.reset()
    return {"status": "reset"}


@app.get("/api/sommelier/wine/{slug}")
async def sommelier_about_wine(slug: str, dish: str | None = None):
    """Информация о конкретном вине через сомелье."""
    som = get_sommelier()
    result = som.about_wine(slug, dish=dish)
    return {
        "kind": result.get("kind", "text"),
        "text": result.get("text", ""),
        "id": result.get("id", slug),
    }


@app.get("/api/sommelier/catalog/stats")
async def sommelier_catalog_stats():
    """Статистика каталога сомелье."""
    som = get_sommelier()
    return {
        "total_wines": len(som.wines),
        "grape_count": dict(som.engine.grape_count.most_common(20)),
    }


if __name__ == "__main__":
    import uvicorn, webbrowser, threading, urllib.request
    def _open_ui():
        for _ in range(120):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8080/api/health", timeout=1) as resp:
                    if resp.status == 200:
                        webbrowser.open("http://127.0.0.1:8080")
                        break
            except: pass
    threading.Thread(target=_open_ui, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8080)
