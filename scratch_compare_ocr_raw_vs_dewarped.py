import time
import cv2
import numpy as np
import os
import json
from pipeline.dewarp_engine import CylindricalDewarpEngine

engine = CylindricalDewarpEngine(use_gpu=True)
ocr = engine.stage5

test_files = [
    ("Castillo de Liria", "test_dataset/butilki/photo_2026-08-10_12-34-29.jpg"),
    ("Barakiani",         "test_dataset/butilki/photo_2026-08-10_12-34-31.jpg"),
    ("Belbek Muscat",     "test_dataset/butilki/photo_2026-08-11_21-10-10.jpg"),
    ("Alma Valley",       "test_dataset/butilki/photo_2026-08-11_21-10-16.jpg"),
]

results = []
artifacts_dir = r"C:\Users\User\.gemini\antigravity-ide\brain\ca6cdc5d-a974-48ab-a177-476bfd71d71d"

for name, path in test_files:
    img = cv2.imread(path)
    if img is None:
        continue
    
    # ------------------------------------------------------------------
    # MODE A: Прямое распознавание БЕЗ развертки (Raw Crop)
    # ------------------------------------------------------------------
    t0_raw = time.perf_counter()
    crop_bgr, mask, bbox = engine.stage1.segment_bottle_and_label(img)
    t_crop_ms = (time.perf_counter() - t0_raw) * 1000
    
    t_ocr_raw_start = time.perf_counter()
    ocr_raw = ocr.process(crop_bgr)
    t_ocr_raw_ms = (time.perf_counter() - t_ocr_raw_start) * 1000
    t_total_raw_ms = (time.perf_counter() - t0_raw) * 1000
    
    # ------------------------------------------------------------------
    # MODE B: Распознавание С разверткой VINA (Dewarped Scan)
    # ------------------------------------------------------------------
    t0_dewarp = time.perf_counter()
    res_dewarp = engine.process_image(img)
    t_total_dewarp_ms = (time.perf_counter() - t0_dewarp) * 1000
    
    # Collect statistics
    raw_tokens = [t["text"] for t in ocr_raw.get("text_blocks", [])]
    raw_confs = [t["confidence"] for t in ocr_raw.get("text_blocks", [])]
    avg_conf_raw = float(np.mean(raw_confs) * 100) if raw_confs else 0.0
    
    dewarp_tokens = [t["text"] for t in res_dewarp.get("text_blocks", [])]
    dewarp_confs = [t["confidence"] for t in res_dewarp.get("text_blocks", [])]
    avg_conf_dewarp = float(np.mean(dewarp_confs) * 100) if dewarp_confs else 0.0
    
    # Generate side-by-side comparison image
    raw_vis = ocr_raw["annotated_bgr"]
    
    # Decode / fetch dewarped annotated
    stage5_dewarp_vis = cv2.imdecode(np.frombuffer(cv2.imencode('.png', res_dewarp['artifacts']['annotated'].encode('latin1'))[1], np.uint8), cv2.IMREAD_COLOR) if False else None
    
    # Let's save both images directly
    fname_clean = name.lower().replace(" ", "_")
    cv2.imwrite(os.path.join(artifacts_dir, f"cmp_{fname_clean}_raw.png"), raw_vis)
    
    # We can get dewarped annotated directly from processing dewarped image:
    res_s4_dewarped = engine.stage4.process(crop_bgr, engine.stage3.process(crop_bgr, engine.stage2.process(crop_bgr, crop_bgr, mask=mask)["text_lines"], engine.stage2.process(crop_bgr, crop_bgr, mask=mask)["line_segments"], engine.stage2.process(crop_bgr, crop_bgr, mask=mask)["cam_orientation"], mask, label_boundaries=engine.stage2.process(crop_bgr, crop_bgr, mask=mask).get("label_boundaries")))
    dewarped_annotated = ocr.process(res_s4_dewarped["dewarped_bgr"])["annotated_bgr"]
    cv2.imwrite(os.path.join(artifacts_dir, f"cmp_{fname_clean}_dewarped.png"), dewarped_annotated)
    
    # Create Side-by-Side montage
    target_h = 500
    w_raw = int(raw_vis.shape[1] * (target_h / raw_vis.shape[0]))
    raw_resized = cv2.resize(raw_vis, (w_raw, target_h), interpolation=cv2.INTER_AREA)
    
    w_dewarp = int(dewarped_annotated.shape[1] * (target_h / dewarped_annotated.shape[0]))
    dewarp_resized = cv2.resize(dewarped_annotated, (w_dewarp, target_h), interpolation=cv2.INTER_AREA)
    
    # Header banner
    header = np.zeros((45, w_raw + w_dewarp + 12, 3), dtype=np.uint8) + 35
    cv2.putText(header, f"БЕЗ РАЗВЕРТКИ ({item_time:=.1f}ms)" if False else f"БЕЗ РАЗВЕРТКИ (Сырой снимок) - {len(raw_tokens)} токенов", (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 255), 2, cv2.LINE_AA)
    cv2.putText(header, f"С РАЗВЕРТКОЙ VINA - {len(dewarp_tokens)} токенов", (w_raw + 25, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 120), 2, cv2.LINE_AA)
    
    divider = np.zeros((target_h, 12, 3), dtype=np.uint8) + 80
    montage_body = np.hstack((raw_resized, divider, dewarp_resized))
    montage = np.vstack((header, montage_body))
    cv2.imwrite(os.path.join(artifacts_dir, f"cmp_side_by_side_{fname_clean}.png"), montage)
    
    item = {
        "name": name,
        "path": path,
        "raw": {
            "crop_time_ms": round(t_crop_ms, 1),
            "ocr_time_ms": round(t_ocr_raw_ms, 1),
            "total_time_ms": round(t_total_raw_ms, 1),
            "num_tokens": len(raw_tokens),
            "tokens": raw_tokens,
            "avg_confidence": round(avg_conf_raw, 1),
            "full_text": ocr_raw.get("full_text", "")
        },
        "dewarped": {
            "total_time_ms": round(t_total_dewarp_ms, 1),
            "num_tokens": len(dewarp_tokens),
            "tokens": dewarp_tokens,
            "avg_confidence": round(avg_conf_dewarp, 1),
            "full_text": res_dewarp.get("full_text", "")
        }
    }
    results.append(item)
    
    print(f"\n=================== {name} ===================")
    print(f"  [БЕЗ РАЗВЕРТКИ] Время: {item['raw']['total_time_ms']:.1f} ms | Токенов: {item['raw']['num_tokens']} | Уверенность: {item['raw']['avg_confidence']}%")
    print(f"    Распознанный текст: {item['raw']['full_text']}")
    print(f"  [С РАЗВЕРТКОЙ]  Время: {item['dewarped']['total_time_ms']:.1f} ms | Токенов: {item['dewarped']['num_tokens']} | Уверенность: {item['dewarped']['avg_confidence']}%")
    print(f"    Распознанный текст: {item['dewarped']['full_text']}")

# Save detailed JSON summary
with open(os.path.join(artifacts_dir, "ocr_comparison_raw_vs_dewarped.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("\nBenchmark completed and montages saved successfully!")
