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

img_bgr = cv2.imread('eval/queries/eval_photo_097.webp')
h, w = img_bgr.shape[:2]
print(f'Profiling on eval_photo_097.webp: {w}x{h} ({w*h/1e6:.1f} MP)')

# Warmup GPU
_ = search.get_embedding(Image.fromarray(cv2.cvtColor(img_bgr[:500, :500], cv2.COLOR_BGR2RGB)))

# 1. Warmup pass
print("\n--- RUN 1 (Warmup / Cold load) ---")
_ = engine.process_image(img_bgr)

# 2. Real hot pass
print("\n--- RUN 2 (Hot GPU / Realistic timing) ---")
t0 = time.perf_counter()
t_start = t0

vina_res = engine.process_image(img_bgr)
t_dewarp = (time.perf_counter() - t0) * 1000.0

t0 = time.perf_counter()
s_sig, s_dino = ranker.embedding_scores(img_bgr)
t_emb = (time.perf_counter() - t0) * 1000.0

t0 = time.perf_counter()
ocr_text = vina_res.get('full_text', '')
ranked = ranker.rank(img_bgr, ocr_text, top_n=6, s_sig=s_sig, s_dino=s_dino)
t_rank = (time.perf_counter() - t0) * 1000.0

total_ms = (time.perf_counter() - t_start) * 1000.0

print('\nHOT GPU TIMING BREAKDOWN:')
print(f'  1. CylindricalDewarpEngine (YOLO + Dewarp + VLM): {t_dewarp:.1f} ms')
print(f'     - Details: {vina_res.get("timings", {})}')
print(f'  2. Embeddings (SigLIP2 + DINOv2-LoRA): {t_emb:.1f} ms')
print(f'  3. Hybrid Ranker: {t_rank:.1f} ms')
print(f'  TOTAL: {total_ms:.1f} ms ({total_ms/1000.0:.2f} s)')
if ranked:
    print(f'  Predicted: {ranked[0]["slug"]} (IF: {ranked[0]["IF"]})')
