# -*- coding: utf-8 -*-
with open("app.py", "r", encoding="utf-8") as f:
    text = f.read()

target1 = """            if not is_in_catalog:
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
            }"""

replacement1 = """            req_id = None
            if not is_in_catalog:
                miss_res = log_missing_wine(source="scanner", query_text=ocr_text, img_bgr=img_bgr, confidence=final_conf)
                req_id = miss_res.get("id")

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
                "req_id": req_id,
                "engine": "hybrid_v2 (SigLIP2 + DINOv2-LoRA + OCR Formula)",
                "total_time_ms": round((time.time() - t0) * 1000, 1),
            }"""

assert target1 in text, "Target 1 not found in app.py"
text = text.replace(target1, replacement1, 1)

target2 = """class MissingWineReportRequest(BaseModel):
    source: str = "catalog_search"
    query_text: str = ""

@app.post("/api/missing-wines/report")
async def report_missing_wine(req: MissingWineReportRequest):
    res = log_missing_wine(source=req.source, query_text=req.query_text)
    return res"""

replacement2 = """class MissingWineReportRequest(BaseModel):
    source: str = "scanner"
    query_text: str = ""
    req_id: str | None = None
    image_base64: str | None = None

@app.post("/api/missing-wines/report")
async def report_missing_wine(req: MissingWineReportRequest):
    if req.req_id:
        update_request_status(req.req_id, "user_requested_addition", "Пользователь подтвердил отправку разработчикам")
        return {"success": True, "id": req.req_id, "message": "Запрос подтвержден и отправлен разработчикам"}

    img_bgr = None
    if req.image_base64 and "," in req.image_base64:
        try:
            b64_str = req.image_base64.split(",", 1)[1]
            raw_bytes = base64.b64decode(b64_str)
            nparr = np.frombuffer(raw_bytes, np.uint8)
            img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"[missing_wines] Error decoding image_base64: {e}")

    res = log_missing_wine(source=req.source, query_text=req.query_text, img_bgr=img_bgr)
    return res"""

assert target2 in text, "Target 2 not found in app.py"
text = text.replace(target2, replacement2, 1)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(text)

print("SUCCESS: app.py updated!")
