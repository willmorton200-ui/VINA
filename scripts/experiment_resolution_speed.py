import cv2, time, torch, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.catalog import WineCatalog
from pipeline.search_engine import WineSearchEngine
from pipeline.dino_engine import DinoLabelEngine
from pipeline.dewarp_engine import CylindricalDewarpEngine
from pipeline.hybrid_ranker import HybridRanker
from PIL import Image

cat = WineCatalog('wines_integrated_clean.csv')
engine = CylindricalDewarpEngine(use_gpu=True)
search = WineSearchEngine(cat, use_gpu=True)
dino = DinoLabelEngine(cat, use_gpu=True)
ranker = HybridRanker(search, dino, cat, w_siglip=0.7, w_dino=0.3, pool_k_sig=15, pool_k_dino=15, calibrate=True)

# Warmup GPU
img_warm = cv2.imread('eval/queries/eval_photo_097.webp')
_ = engine.process_image(img_warm[:500, :500])

print("=" * 80)
print("  ЭКСПЕРИМЕНТ: СКОРОСТЬ vs РАЗРЕШЕНИЕ НА САМОМ БОЛЬШОМ КАДРЕ 097 (16.0 Мп)")
print("=" * 80)

resolutions = [1600, 2000, 2400, 2800, None] # None = Full resolution

for max_dim in resolutions:
    img = cv2.imread('eval/queries/eval_photo_097.webp')
    h, w = img.shape[:2]
    
    t_resize_0 = time.perf_counter()
    if max_dim is not None and max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    t_res = (time.perf_counter() - t_resize_0) * 1000.0
    
    cur_h, cur_w = img.shape[:2]
    
    t_start = time.perf_counter()
    vina_res = engine.process_image(img)
    t_dew = (time.perf_counter() - t_start) * 1000.0
    
    t0 = time.perf_counter()
    s_sig, s_dino = ranker.embedding_scores(img)
    t_emb = (time.perf_counter() - t0) * 1000.0
    
    t0 = time.perf_counter()
    ocr_text = vina_res.get('full_text', '')
    ranked = ranker.rank(img, ocr_text, top_n=3, s_sig=s_sig, s_dino=s_dino)
    t_rnk = (time.perf_counter() - t0) * 1000.0
    
    total = (time.perf_counter() - t_start) * 1000.0
    
    best = ranked[0] if ranked else {}
    print(f"\n[Max Dim: {str(max_dim):<6}] Resolution: {cur_w}x{cur_h} ({cur_w*cur_h/1e6:.1f} MP)")
    print(f"  Time: TOTAL={total:.0f} ms | YOLO+Dew={t_dew:.0f} ms | Emb={t_emb:.0f} ms | Rank={t_rnk:.0f} ms")
    print(f"  Stage1 YOLO time: {vina_res.get('timings', {}).get('stage1_ms', 0)} ms")
    print(f"  Stage5 VLM time : {vina_res.get('timings', {}).get('stage5_ms', 0)} ms")
    print(f"  Winner: {best.get('slug')} (IF: {best.get('IF')}%, N: {best.get('N')}%)")
    print(f"  OCR: '{ocr_text[:80]}...'")

print("\n" + "=" * 80)
print("  ТЕСТ КРИТИЧЕСКИХ СЛОЖНЫХ КАДРОВ С МИКРО-ТЕКСТОМ (028 и 065)")
print("=" * 80)

critical_cases = [
    ('eval_photo_028.webp', 'leto-kaberne-fran-2024-polusladkoe-krasnoe'),
    ('eval_photo_065.webp', 'litavschukov-Sovinon-Blanc-beloe-polusladkoe'),
]

for fname, exp_slug in critical_cases:
    print(f"\n--- Тест {fname} (Ожидался: {exp_slug}) ---")
    orig_img = cv2.imread(f'eval/queries/{fname}')
    oh, ow = orig_img.shape[:2]
    
    for max_dim in [1600, 2000, 2400, None]:
        test_img = orig_img.copy()
        if max_dim is not None and max(oh, ow) > max_dim:
            scale = max_dim / float(max(oh, ow))
            test_img = cv2.resize(test_img, (int(ow * scale), int(oh * scale)), interpolation=cv2.INTER_AREA)
        
        t0 = time.perf_counter()
        v_res = engine.process_image(test_img)
        s_s, s_d = ranker.embedding_scores(test_img)
        r = ranker.rank(test_img, v_res.get('full_text', ''), top_n=2, s_sig=s_s, s_dino=s_d)
        dur = (time.perf_counter() - t0) * 1000.0
        
        pred = r[0]['slug'] if r else None
        conf = r[0]['IF'] if r else 0
        match = "✓ OK" if pred == exp_slug else "✗ FAIL"
        ocr_sub = v_res.get('full_text', '').replace('\n', ' ')
        print(f"  Dim: {str(max_dim):<5} -> {match} | Time: {dur:.0f} ms | Pred: {pred} ({conf}%) | OCR: '{ocr_sub[:60]}'")
