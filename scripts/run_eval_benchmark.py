import requests
import json
import time
from pathlib import Path

url = "http://127.0.0.1:8080/v1/eval/predict"

with open("eval/mapping.json", "r", encoding="utf-8") as f:
    mapping_data = json.load(f)

cases = mapping_data["cases"]
total = len(cases)
results = []

print(f"Запуск полного теста {total} бутылок...")
t_start = time.time()

for idx, c in enumerate(cases):
    qid = c["query_id"]
    fname = c["image_path"]
    exp = c["expected_slug"]
    img_path = Path("eval/queries") / fname
    
    t0 = time.time()
    try:
        with open(img_path, "rb") as f:
            resp = requests.post(url, files={"image": (fname, f, "image/webp")}, timeout=60)
        res = resp.json()
        pred = res.get("slug")
        conf = res.get("confidence_percent", 0.0)
        ms = round((time.time() - t0) * 1000)
    except Exception as e:
        pred = None
        conf = 0.0
        ms = 0
        
    ok = (pred == exp)
    results.append({
        "query_id": qid,
        "file": fname,
        "expected": exp,
        "predicted": pred,
        "confidence": conf,
        "ok": ok,
        "time_ms": ms
    })
    
    status_str = "✓ OK" if ok else "✗ FAIL"
    print(f"[{idx+1:03d}/{total:03d}] {qid} ({fname}) -> {status_str} | Pred: {str(pred)[:32]:<32} | Exp: {str(exp)[:32]:<32} | {conf}% ({ms} ms)")

correct = sum(1 for r in results if r["ok"])
elapsed = round(time.time() - t_start, 1)

print("=" * 90)
print(f"ИТОГОВЫЙ СЧЕТ: {correct}/{total} ({correct/total*100:.1f}%) за {elapsed} с")
print("=" * 90)

fails = [r for r in results if not r["ok"]]
if fails:
    print(f"Список несовпадений ({len(fails)} шт):")
    for f in fails:
        print(f"  {f['query_id']} ({f['file']}) -> Expected: {f['expected']}, Predicted: {f['predicted']}, Conf: {f['confidence']} %")
else:
    print("ВСЕ 100 БУТЫЛОК РАСПОЗНАНЫ БЕЗОШИБОЧНО!")

# Сохраняем свежие predictions
out_path = Path("eval/predictions.jsonl")
with open(out_path, "w", encoding="utf-8") as f:
    for r in results:
        entry = {
            "query_id": r["query_id"],
            "image_path": r["file"],
            "predicted_slug": r["predicted"],
            "confidence": r["confidence"],
            "latency_ms": r["time_ms"]
        }
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
print(f"Результаты сохранены в {out_path}")
