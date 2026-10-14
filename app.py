
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
from pipeline.color_matcher import calculate_structural_orb_matches
from pipeline.dino_engine import DinoLabelEngine
from pipeline.hybrid_ranker import HybridRanker

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

# ---- Hybrid Ranker v2: SigLIP2 + DINOv2-LoRA ----
dino_available = False
dino_engine = None
ranker = None
try:
    dino_engine = DinoLabelEngine(catalog, use_gpu=gpu_available, yolo_model=engine.stage1.yolo_model)
    ranker = HybridRanker(search_engine, dino_engine, catalog, w_siglip=0.7, w_dino=0.3, pool_k_sig=15, pool_k_dino=15, calibrate=True)
    dino_available = True
    print("[app.py] HybridRanker v2 (SigLIP2 + DINOv2-LoRA + Calibrated Fusion + Sister Cluster Pool) initialized.")
    print("[app.py] 4. Потолок пула (GT в кандидатах Top-3+Top-3): Набор 1: 27/27, Набор 2: 23/25 -> Всего: 50/52 (96.2%).")
except Exception as e:
    print(f"[app.py] Warning: DINO initialization failed ({e}), falling back to SigLIP only.")

# ---- Sommelier (ленивая инициализация) ----
_sommelier = None

def get_sommelier():
    global _sommelier
    if _sommelier is None:
        from sommelier.sommelier import Sommelier
        _sommelier = Sommelier()
    return _sommelier

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEST_DATASET_DIR = BASE_DIR / "test_dataset"

# ---- Static mounts ----
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    if (STATIC_DIR / "img").exists():
        app.mount("/img", StaticFiles(directory=str(STATIC_DIR / "img")), name="root_img")
    if (STATIC_DIR / "svg").exists():
        app.mount("/svg", StaticFiles(directory=str(STATIC_DIR / "svg")), name="root_svg")

if TEST_DATASET_DIR.exists():
    app.mount("/test_dataset", StaticFiles(directory=str(TEST_DATASET_DIR)), name="test_dataset")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(str(index_file), "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VINA Scanner API is running</h1>"

@app.get("/scanner", response_class=HTMLResponse)
async def serve_scanner():
    scanner_file = STATIC_DIR / "scanner.html"
    if scanner_file.exists():
        with open(str(scanner_file), "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Scanner UI not found</h1>"

@app.get("/map", response_class=HTMLResponse)
async def serve_map():
    map_file = STATIC_DIR / "map_demo.html"
    if map_file.exists():
        with open(str(map_file), "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Map UI not found</h1>"

@app.get("/style.css")
async def get_style_css():
    p = STATIC_DIR / "style.css"
    return FileResponse(str(p), media_type="text/css") if p.exists() else JSONResponse({"error": "not found"}, 404)

@app.get("/app.js")
async def get_app_js():
    p = STATIC_DIR / "app.js"
    return FileResponse(str(p), media_type="application/javascript") if p.exists() else JSONResponse({"error": "not found"}, 404)

@app.get("/scanner.css")
async def get_scanner_css():
    p = STATIC_DIR / "scanner.css"
    return FileResponse(str(p), media_type="text/css") if p.exists() else JSONResponse({"error": "not found"}, 404)

@app.get("/scanner.js")
async def get_scanner_js():
    p = STATIC_DIR / "scanner.js"
    return FileResponse(str(p), media_type="application/javascript") if p.exists() else JSONResponse({"error": "not found"}, 404)

@app.get("/scanner.html", response_class=HTMLResponse)
async def get_scanner_html():
    p = STATIC_DIR / "scanner.html"
    return FileResponse(str(p), media_type="text/html") if p.exists() else JSONResponse({"error": "not found"}, 404)

@app.get("/znak.png")
async def get_znak():
    p = STATIC_DIR / "znak.png"
    return FileResponse(str(p), media_type="image/png") if p.exists() else JSONResponse({"error": "not found"}, 404)

@app.get("/badge_glass.png")
async def get_badge():
    p = STATIC_DIR / "badge_glass.png"
    return FileResponse(str(p), media_type="image/png") if p.exists() else JSONResponse({"error": "not found"}, 404)

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
        "dino_available": dino_available,
        "dino_index_size": dino_engine.index.ntotal if (dino_engine and dino_engine.index) else 0,
        "ranker_mode": "Hybrid v2 (SigLIP2 + DINOv2-LoRA + OCR Formula)" if dino_available else "SigLIP-only (legacy)",
        "cascade_info": "Top-3 SigLIP + Top-3 DINO + OCR Bonus Formula IF = N + IB*(A+C+D+F)",
        "pool_ceiling": "27/27 (Набор 1), 23/25 (Набор 2) -> 50/52 (96.2%)",
    }

@app.get("/api/samples")
async def list_sample_bottles():
    butilki_dir = TEST_DATASET_DIR / "butilki"
    cam_dir = TEST_DATASET_DIR / "cam"
    cat_dir = TEST_DATASET_DIR / "calalog"
    samples = []
    for d, folder in [(butilki_dir, "butilki"), (cam_dir, "cam")]:
        if not d.exists():
            continue
        for fpath in sorted(glob.glob(os.path.join(str(d), "*.*"))):
            fname = os.path.basename(fpath)
            base_id = fname.split('_')[0]
            cat_matches = glob.glob(os.path.join(str(cat_dir), f"{base_id}_*")) if cat_dir.exists() else []
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
    path1 = TEST_DATASET_DIR / "butilki" / req.sample_filename
    path2 = TEST_DATASET_DIR / "cam" / req.sample_filename
    img_path = str(path1) if path1.exists() else str(path2)
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Sample image not found")
    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Failed to decode sample image")
    base_id = req.sample_filename.split('_')[0]
    cat_matches = glob.glob(os.path.join(str(TEST_DATASET_DIR / "calalog"), f"{base_id}_*")) if (TEST_DATASET_DIR / "calalog").exists() else []
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

CONFIDENCE_THRESHOLD = 86.0  # Порог проходимости итоговой уверенности (всё что < 86% считается отсутствующим в каталоге)

@app.post("/v1/eval/predict")
async def eval_predict(image: UploadFile = File(...)):
    """
    Гибридный эндпоинт v2:
    - Выпрямление этикетки CylindricalDewarpEngine & OCR
    - Эмбеддинги SigLIP2 + DINOv2-LoRA
    - Калиброванное слияние (Z-Score)
    - Формула бонусов ТЗ Алексея: IF = N + IB * (0.50A + 0.25C + 0.15D + 0.10F)
    - Порог проходимости итоговой уверенности: 86%
    """
    t0 = time.time()
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

    # Пре-ресайз до 1600px для 12-мегапиксельных фото (ускорение в 5-10 раз)
    h_in, w_in = img_bgr.shape[:2]
    if max(h_in, w_in) > 1600:
        scale_in = 1600.0 / max(h_in, w_in)
        img_bgr = cv2.resize(img_bgr, (int(w_in * scale_in), int(h_in * scale_in)), interpolation=cv2.INTER_AREA)

    # ШАГ 1: VINA STUDIO (Выпрямление & OCR)
    dewarped_img = None
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
    except Exception as e:
        print(f"[eval_predict] VINA STUDIO dewarp error: {e}")

    # ШАГ 2: Гибридное ранжирование (если ranker активен)
    if ranker is not None:
        s_sig, s_dino = ranker.embedding_scores(img_bgr)
        # Если выпрямленная этикетка получена, объединяем максимум для SigLIP
        if dewarped_img is not None and dewarped_img.size > 0:
            try:
                from PIL import Image as _PILImage
                pil_dew = _PILImage.fromarray(cv2.cvtColor(dewarped_img, cv2.COLOR_BGR2RGB))
                s_sig_dew = ranker._all_scores(search_engine.index, search_engine.slugs, search_engine.get_embedding(pil_dew))
                for sl, sc in s_sig_dew.items():
                    if sc > s_sig.get(sl, 0.0):
                        s_sig[sl] = sc
            except Exception as e_dew:
                print(f"[eval_predict] Dewarped embedding error: {e_dew}")

        ranked = ranker.rank(img_bgr, ocr_text, top_n=6, s_sig=s_sig, s_dino=s_dino)
        if ranked:
            best = ranked[0]
            best_slug = best["slug"]
            wine_info = catalog.get_wine(best_slug) or {}
            
            candidates = []
            for r in ranked:
                c_slug = r["slug"]
                c_wine = catalog.get_wine(c_slug) or {}
                b_sum = round(r["A"] + r["C"] + r["D"] + r["F"], 2)
                candidates.append({
                    "slug": c_slug,
                    "name": c_wine.get("name", r.get("name", "")),
                    "score": round(r["IF"] / 100.0, 4),
                    "final_confidence": r["IF"],
                    "confidence_embedding": r["N"],
                    "ocr_bonus": b_sum,
                    "bonus_breakdown": {"A": r["A"], "C": r["C"], "D": r["D"], "F": r["F"]},
                    "matched": r.get("matched", {}),
                    "siglip_raw": r.get("siglip_raw", 0.0),
                    "dino_raw": r.get("dino_raw", 0.0),
                })

            best_bonus = round(best["A"] + best["C"] + best["D"] + best["F"], 2)
            final_conf = round(best["IF"], 2)
            is_in_catalog = final_conf >= CONFIDENCE_THRESHOLD

            return {
                "slug": best_slug if is_in_catalog else None,
                "name": wine_info.get("name", "") if is_in_catalog else "",
                "score": round(best["IF"] / 100.0, 4),
                "confidence": round(best["IF"] / 100.0, 4),
                "confidence_percent": final_conf,
                "confidence_embedding": round(best["N"], 2),
                "ocr_bonus": best_bonus,
                "bonus_breakdown": {"A": best["A"], "C": best["C"], "D": best["D"], "F": best["F"]},
                "matched_words": best.get("matched", {}),
                "ocr_text": ocr_text[:200] if ocr_text else "",
                "candidates": candidates,
                "status": "found" if is_in_catalog else "not_in_catalog",
                "engine": "hybrid_v2 (SigLIP2 + DINOv2-LoRA + OCR Formula)",
                "total_time_ms": round((time.time() - t0) * 1000, 1),
            }

    # ФОЛЛБЕК (если DINO не загрузился): Legacy SigLIP + VinaStudioMatcher
    siglip_results = search_engine.search_by_cv2_image(img_bgr, top_k=20)
    sorted_candidates = sorted(siglip_results, key=lambda x: x["score"], reverse=True)[:20]
    cascade_result = vina_matcher.cascade_decision(ocr_text, sorted_candidates)
    candidates = cascade_result.get("candidates", [])
    candidates = sorted(candidates, key=lambda x: x.get("final_confidence", 0), reverse=True)
    if not candidates:
        return {
            "slug": None,
            "name": "",
            "score": 0.0,
            "confidence": 0.0,
            "confidence_percent": 0.0,
            "confidence_embedding": 0.0,
            "ocr_bonus": 0.0,
            "ocr_text": ocr_text[:200] if ocr_text else "",
            "candidates": [],
            "status": "not_in_catalog",
            "engine": "legacy_fallback (SigLIP only)",
            "total_time_ms": round((time.time() - t0) * 1000, 1),
        }

    best_candidate = candidates[0]
    best_slug = best_candidate["slug"]
    wine_info = catalog.get_wine(best_slug) or {}
    final_conf = round(best_candidate.get("final_confidence", 0.0), 2)
    is_in_catalog = final_conf >= CONFIDENCE_THRESHOLD

    return {
        "slug": best_slug if is_in_catalog else None,
        "name": wine_info.get("name", "") if is_in_catalog else "",
        "score": round(best_candidate.get("score", 0.0), 4),
        "confidence": round(final_conf / 100.0, 4),
        "confidence_percent": final_conf,
        "confidence_embedding": best_candidate.get("confidence_embedding", 0.0),
        "ocr_bonus": best_candidate.get("ocr_bonus", 0.0),
        "ocr_text": ocr_text[:200] if ocr_text else "",
        "candidates": candidates,
        "status": "found" if is_in_catalog else "not_in_catalog",
        "engine": "legacy_fallback (SigLIP only)",
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
