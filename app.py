"""
FastAPI Server for VINA Cylindrical Dewarping & OCR System
"""

import os
import glob
import cv2
import numpy as np
import torch
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline import CylindricalDewarpEngine, compute_image_metrics

app = FastAPI(title="VINA Cylindrical Dewarping Studio", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine singleton
gpu_available = torch.cuda.is_available()
engine = CylindricalDewarpEngine(use_gpu=gpu_available)

# Mount static folder
app.mount("/static", StaticFiles(directory="d:/VINA/static"), name="static")
app.mount("/test_dataset", StaticFiles(directory="d:/VINA/test_dataset"), name="test_dataset")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("d:/VINA/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/health")
async def health_check():
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "None (CPU)"
    return {
        "status": "healthy",
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "torch_version": torch.__version__,
        "pipeline_stages": [
            "1. Localization & Preprocessing (YOLOv8-seg, SAM ViT-H, Largest Component)",
            "2. Geometric Feature Extraction (4 Exact Physical Corners, Lateral Lines)",
            "3. Cylindrical Grid Optimization (Coon's Patch Transfinite Grid)",
            "4. Backward Deformation Remapping (TPS, Lanczos-4)",
            "5. Character Recognition & Code Decoding (EasyOCR GPU)"
        ]
    }

@app.get("/api/samples")
async def list_sample_bottles():
    """Lists available test bottles from test_dataset/butilki and test_dataset/cam."""
    butilki_dir = "d:/VINA/test_dataset/butilki"
    cam_dir = "d:/VINA/test_dataset/cam"
    cat_dir = "d:/VINA/test_dataset/calalog"
    
    samples = []
    
    # Priority: User dataset 'butilki'
    butilki_files = sorted(glob.glob(os.path.join(butilki_dir, "*.*")))
    for fpath in butilki_files:
        fname = os.path.basename(fpath)
        base_id = fname.split('_')[0]
        
        cat_matches = glob.glob(os.path.join(cat_dir, f"{base_id}_*"))
        has_catalog = len(cat_matches) > 0
        cat_rel = f"/test_dataset/calalog/{os.path.basename(cat_matches[0])}" if has_catalog else None

        display_title = fname.replace(".jpeg", "").replace(".jpg", "").replace(".png", "").replace("_", " ")
        if len(display_title) > 35:
            display_title = display_title[:32] + "..."

        samples.append({
            "id": base_id,
            "filename": fname,
            "folder": "butilki",
            "title": display_title,
            "cam_url": f"/test_dataset/butilki/{fname}",
            "cat_url": cat_rel,
            "has_catalog": has_catalog
        })

    # Also include cam dataset if any
    cam_files = sorted(glob.glob(os.path.join(cam_dir, "*.*")))
    for fpath in cam_files:
        fname = os.path.basename(fpath)
        base_id = fname.split('_')[0]
        cat_matches = glob.glob(os.path.join(cat_dir, f"{base_id}_*"))
        has_catalog = len(cat_matches) > 0
        cat_rel = f"/test_dataset/calalog/{os.path.basename(cat_matches[0])}" if has_catalog else None

        display_title = fname.replace(".jpeg", "").replace(".jpg", "").replace("_", " ")
        if len(display_title) > 35:
            display_title = display_title[:32] + "..."

        samples.append({
            "id": base_id,
            "filename": fname,
            "folder": "cam",
            "title": display_title,
            "cam_url": f"/test_dataset/cam/{fname}",
            "cat_url": cat_rel,
            "has_catalog": has_catalog
        })

    return {"samples": samples}

class ProcessSampleRequest(BaseModel):
    sample_filename: str

@app.post("/api/process_sample")
async def process_sample(req: ProcessSampleRequest):
    # Check in butilki first, then in cam
    path1 = os.path.join("d:/VINA/test_dataset/butilki", req.sample_filename)
    path2 = os.path.join("d:/VINA/test_dataset/cam", req.sample_filename)
    
    img_path = path1 if os.path.exists(path1) else path2
    if not os.path.exists(img_path):
        raise HTTPException(status_code=404, detail="Sample image not found")

    img_bgr = cv2.imread(img_path)
    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Failed to decode sample image")

    # Match catalog if any
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

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    def _open_ui():
        webbrowser.open("http://127.0.0.1:8000")

    threading.Timer(1.2, _open_ui).start()
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
