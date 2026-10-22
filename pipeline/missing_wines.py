# -*- coding: utf-8 -*-
"""
VINA Missing Wines & Search Requests Logger + Dashboard Service
Сбор, сохранение и обработка запросов пользователей на вина, отсутствующие в каталоге.
"""

from __future__ import annotations
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import cv2
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "missing_wines"
IMAGES_DIR = DATA_DIR / "images"
DB_FILE = DATA_DIR / "missing_wines.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

USER_FRIENDLY_MESSAGE = "Данного вина нет в базе, отправить разработчику для добавления в базу?"


def _read_db() -> List[Dict[str, Any]]:
    if not DB_FILE.exists():
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[missing_wines] Error reading DB: {e}")
        return []


def _write_db(records: List[Dict[str, Any]]) -> None:
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[missing_wines] Error writing DB: {e}")


def log_missing_wine(
    source: str,
    query_text: str = "",
    img_bgr: Optional[np.ndarray] = None,
    user_ip: str = "",
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Логгирует отсутствующее вино (от сканера камеры или из поиска каталога).
    """
    req_id = f"req_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    image_url = ""

    if img_bgr is not None and img_bgr.size > 0:
        filename = f"{req_id}.jpg"
        filepath = IMAGES_DIR / filename
        try:
            cv2.imwrite(str(filepath), img_bgr)
            image_url = f"/api/missing-wines/image/{filename}"
        except Exception as e:
            print(f"[missing_wines] Error saving image: {e}")

    record = {
        "id": req_id,
        "timestamp": now_iso,
        "source": source,  # 'scanner' или 'catalog_search'
        "query_text": query_text.strip() if query_text else "",
        "image_url": image_url,
        "user_ip": user_ip,
        "confidence": confidence,
        "status": "pending",  # 'pending', 'in_progress', 'added'
        "admin_notes": "",
    }

    records = _read_db()
    records.insert(0, record)
    _write_db(records)

    return {
        "success": True,
        "id": req_id,
        "message": USER_FRIENDLY_MESSAGE,
        "record": record,
    }


def get_dashboard_summary() -> Dict[str, Any]:
    """
    Формирует сводные данные для дашборда администрации.
    """
    records = _read_db()
    total = len(records)
    pending = sum(1 for r in records if r.get("status") == "pending")
    in_progress = sum(1 for r in records if r.get("status") == "in_progress")
    added = sum(1 for r in records if r.get("status") == "added")

    scanner_count = sum(1 for r in records if r.get("source") == "scanner")
    catalog_count = sum(1 for r in records if r.get("source") == "catalog_search")

    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "added": added,
        "sources": {
            "scanner": scanner_count,
            "catalog_search": catalog_count,
        },
        "records": records[:100],  # последние 100 заявок
    }


def update_request_status(req_id: str, new_status: str, admin_notes: str = "") -> bool:
    records = _read_db()
    found = False
    for r in records:
        if r.get("id") == req_id:
            r["status"] = new_status
            if admin_notes:
                r["admin_notes"] = admin_notes
            found = True
            break
    if found:
        _write_db(records)
    return found
