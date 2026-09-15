import requests
import json
import time

# Test direct engine execution matching app.py
from app import engine, ProcessSampleRequest
import asyncio

async def test_api():
    t0 = time.perf_counter()
    import cv2
    img_bgr = cv2.imread("test_dataset/butilki/photo_2026-08-11_21-10-14.jpg")
    res = engine.process_image(img_bgr)
    t_total = (time.perf_counter() - t0) * 1000.0
    
    print("\n=======================================================")
    print("API / WEB APP DIRECT PIPELINE TEST RESULTS:")
    print("=======================================================")
    print(f"Total Execution Time: {t_total:.1f} ms ({t_total/1000.0:.2f} sec)")
    print(f"Stage 1 (GPU Seg):   {res['timings']['stage1_ms']} ms")
    print(f"Stage 2 (Corners):   {res['timings']['stage2_ms']} ms")
    print(f"Stage 3 (3D Mesh):   {res['timings']['stage3_ms']} ms")
    print(f"Stage 4 (Lanczos-4): {res['timings']['stage4_ms']} ms")
    print(f"Stage 5 (OCR+Dict):  {res['timings']['stage5_ms']} ms")
    print("-------------------------------------------------------")
    print(f"Full Text on Web Page: {res['full_text']}")
    print(f"Number of Tokens:      {res['num_words']}")
    print(f"Lexicon Corrections:   {res['lexicon_corrections']}")
    print("=======================================================")

asyncio.run(test_api())
