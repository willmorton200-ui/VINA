
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
from pipeline.missing_wines import (
    log_missing_wine,
    get_dashboard_summary,
    update_request_status,
    USER_FRIENDLY_MESSAGE,
    IMAGES_DIR as MISSING_WINES_IMAGES_DIR,
)

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

SERVER_BOOT_ID = str(int(time.time()))

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
            html = f.read()
        return HTMLResponse(
            content=html.replace("__SERVER_BOOT_ID__", SERVER_BOOT_ID),
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
        )
    return "<h1>Scanner UI not found</h1>"

@app.get("/map", response_class=HTMLResponse)
async def serve_map():
    map_file = STATIC_DIR / "map_demo.html"
    if map_file.exists():
        with open(str(map_file), "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Map UI not found</h1>"

@app.get("/hub", response_class=HTMLResponse)
async def serve_hub():
    hub_file = STATIC_DIR / "vina_hub.html"
    if hub_file.exists():
        with open(str(hub_file), "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VINA Hub UI not found</h1>"


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
    return FileResponse(str(p), media_type="text/css", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}) if p.exists() else JSONResponse({"error": "not found"}, 404)

@app.get("/scanner.js")
async def get_scanner_js():
    p = STATIC_DIR / "scanner.js"
    return FileResponse(str(p), media_type="application/javascript", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}) if p.exists() else JSONResponse({"error": "not found"}, 404)

@app.get("/scanner.html", response_class=HTMLResponse)
async def get_scanner_html():
    p = STATIC_DIR / "scanner.html"
    if p.exists():
        with open(str(p), "r", encoding="utf-8") as f:
            html = f.read()
        return HTMLResponse(
            content=html.replace("__SERVER_BOOT_ID__", SERVER_BOOT_ID),
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
        )
    return JSONResponse({"error": "not found"}, 404)

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
        "boot_id": SERVER_BOOT_ID,
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

CONFIDENCE_THRESHOLD = 50.0  # Порог проходимости итоговой уверенности (всё что >= 50% признается найденным в каталоге)

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

    h_orig, w_orig = img_bgr.shape[:2]
    if h_orig > 1920 and w_orig > 1080:
        scale_in = max(1920.0 / float(h_orig), 1080.0 / float(w_orig))
        if scale_in < 1.0:
            img_bgr = cv2.resize(img_bgr, (int(round(w_orig * scale_in)), int(round(h_orig * scale_in))), interpolation=cv2.INTER_AREA)


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

            if not is_in_catalog:
                log_missing_wine(source="scanner", query_text=ocr_text, img_bgr=img_bgr, confidence=final_conf)

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
                "message": "" if is_in_catalog else USER_FRIENDLY_MESSAGE,
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
        log_missing_wine(source="scanner", query_text=ocr_text, img_bgr=img_bgr, confidence=0.0)
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
            "message": USER_FRIENDLY_MESSAGE,
            "engine": "legacy_fallback (SigLIP only)",
            "total_time_ms": round((time.time() - t0) * 1000, 1),
        }

    best_candidate = candidates[0]
    best_slug = best_candidate["slug"]
    wine_info = catalog.get_wine(best_slug) or {}
    final_conf = round(best_candidate.get("final_confidence", 0.0), 2)
    is_in_catalog = final_conf >= CONFIDENCE_THRESHOLD

    if not is_in_catalog:
        log_missing_wine(source="scanner", query_text=ocr_text, img_bgr=img_bgr, confidence=final_conf)

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
        "message": "" if is_in_catalog else USER_FRIENDLY_MESSAGE,
        "engine": "legacy_fallback (SigLIP only)",
        "total_time_ms": round((time.time() - t0) * 1000, 1),
    }

# ---- Missing Wines & Admin Dashboard Endpoints ----
@app.get("/api/missing-wines/image/{filename}")
async def get_missing_wine_image(filename: str):
    img_path = MISSING_WINES_IMAGES_DIR / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(str(img_path))

class MissingWineReportRequest(BaseModel):
    source: str = "catalog_search"
    query_text: str = ""

@app.post("/api/missing-wines/report")
async def report_missing_wine(req: MissingWineReportRequest):
    res = log_missing_wine(source=req.source, query_text=req.query_text)
    return res

@app.get("/api/admin/dashboard/missing-wines")
async def admin_dashboard_missing_wines():
    return get_dashboard_summary()

class UpdateStatusRequest(BaseModel):
    status: str
    admin_notes: str = ""

@app.post("/api/admin/dashboard/missing-wines/{req_id}/status")
async def admin_update_status(req_id: str, req: UpdateStatusRequest):
    ok = update_request_status(req_id, req.status, req.admin_notes)
    if not ok:
        raise HTTPException(status_code=404, detail="Request not found")
    return {"success": True, "id": req_id, "new_status": req.status}


@app.get("/api/wine/{slug}")
async def get_wine_card(slug: str):
    wine = catalog.get_wine(slug)
    if not wine:
        raise HTTPException(status_code=404, detail="Wine not found")
    return wine

@app.get("/api/image/{slug}")
async def get_wine_image(slug: str):
    wine = catalog.get_wine(slug)
    if wine and wine.get("image_path") and os.path.exists(wine["image_path"]):
        return FileResponse(wine["image_path"])

    for base_dir in ["wines_images_clean/wines_images", "/app/wines_images_clean/wines_images", "."]:
        for ext in [".webp", ".png", ".jpg", ".jpeg"]:
            candidate = os.path.join(base_dir, f"{slug}{ext}")
            if os.path.exists(candidate):
                return FileResponse(candidate)

    # 1. Проверяем поле базы «Ссылка на изображение» (колонка 13 датасета)
    remote_url = ""
    if wine:
        remote_url = wine.get("remote_image_url") or wine.get("image_url") or ""
    
    if remote_url and str(remote_url).startswith("http"):
        try:
            cache_dir = Path("wines_images_clean/wines_images")
            cache_dir.mkdir(parents=True, exist_ok=True)
            cached_file = cache_dir / f"{slug}.webp"
            if not cached_file.exists():
                import urllib.request
                req = urllib.request.Request(remote_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        cached_file.write_bytes(resp.read())
            if cached_file.exists():
                return FileResponse(str(cached_file))
        except Exception:
            from fastapi.responses import RedirectResponse
            return RedirectResponse(remote_url)

    for fallback in ["static/badge_glass.png", "/app/static/badge_glass.png"]:
        if os.path.exists(fallback):
            return FileResponse(fallback)
    raise HTTPException(status_code=404, detail="Image not found")


# ============================================================
# Sommelier AI (VINA2) + Pairing + OpenStreetMap + V2 Hub
# ============================================================

from sommelier.service import SommelierService
from sommelier.pairing import build_pairing_service, load_service_wines
from sommelier.dialog_router import router as sommelier_dialog_router
from sommelier.pairing_router import router as sommelier_pairing_router
from sommelier.api_router import (
    sommelier_router as sommelier_v2_router,
    bind_existing_vina_catalog,
    engine as sommelier_v2_engine,
    HISTORICAL_WINES_DB,
)

# 1. App State for Sommelier
app.state.catalog = catalog

SOMMELIER_CSV = BASE_DIR / "sommelier" / "data" / "wines_integrated.csv"
SOMMELIER_FEEDBACK = BASE_DIR / "sommelier" / "data" / "feedback.jsonl"
app.state.sommelier = SommelierService(SOMMELIER_CSV, SOMMELIER_FEEDBACK)

try:
    service_wines, updated_at = load_service_wines(str(SOMMELIER_CSV))
    app.state.sommelier_pairing = build_pairing_service(
        catalog_source="service",
        service_wines=service_wines,
        service_updated_at=updated_at,
    )
    print(f"[app.py] Sommelier Pairing service loaded with {len(service_wines)} catalog wines.")
except Exception as e:
    print(f"[app.py] Warning: could not load service pairing: {e}")
    app.state.sommelier_pairing = build_pairing_service(catalog_source="demo")

# 2. Bind existing VINA catalog for /api/v2 endpoints
try:
    catalog_list = []
    for s, w in catalog.wines_by_slug.items():
        w_copy = dict(w)
        w_copy["sugar"] = w.get("sugar") or w.get("sweetness", "")
        catalog_list.append(w_copy)
    bind_existing_vina_catalog(catalog_list)
except Exception as e:
    print(f"[app.py] Warning: could not bind catalog to Sommelier v2: {e}")

# 3. Include Routers
# /api/sommelier: Dialog endpoints (/ask, /reset, /wine/{slug}, /wine/{slug}/alternatives)
app.include_router(sommelier_dialog_router, prefix="/api")

# /api/sommelier: Pairing endpoints (/pairing/dish, /analog, /pairing/wine/{slug}, /similar/{grape_id}, /grapes, /dishes, /health)
app.include_router(sommelier_pairing_router, prefix="/api")

# /api/v2: Catalog, Facets, History, Full Sommelier, Map Nearby Stores
app.include_router(sommelier_v2_router)


@app.get("/hub", response_class=HTMLResponse)
async def serve_vina_hub():
    """Единый интерфейс с 4 закладками: Сканер, Каталог вин, Карта вин, Сомелье."""
    hub_file = STATIC_DIR / "vina_hub.html"
    if hub_file.exists():
        return FileResponse(str(hub_file), media_type="text/html")
    return "<h1>Файл static/vina_hub.html еще не создан в папке static/</h1>"


@app.get("/api/sommelier/catalog/stats")
async def sommelier_catalog_stats():
    """Статистика каталога сомелье."""
    return {
        "dialog_wines_count": len(app.state.sommelier.wines) if app.state.sommelier else 0,
        "pairing_health": app.state.sommelier_pairing.health() if app.state.sommelier_pairing else {},
        "historical_wines_count": len(HISTORICAL_WINES_DB) if HISTORICAL_WINES_DB else 0,
    }


if __name__ == "__main__":
    import uvicorn, webbrowser, threading, urllib.request
    def _open_ui():
        for _ in range(120):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen("http://127.0.0.1:8080/api/health", timeout=1) as resp:
                    if resp.status == 200:
                        webbrowser.open("http://127.0.0.1:8080/hub")
                        break
            except Exception:
                pass
    threading.Thread(target=_open_ui, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8080)