import time
import cv2
import torch
from pipeline.dewarp_engine import CylindricalDewarpEngine

img = cv2.imread("test_dataset/butilki/photo_2026-08-10_12-34-31.jpg")
engine = CylindricalDewarpEngine(use_gpu=True)

# Warmup
res = engine.process_image(img)

# Profile breakdown
t0 = time.perf_counter()
crop, mask, bbox_info = engine.stage1.segment_bottle_and_label(img)
t1 = time.perf_counter()

features = engine.stage2.extract_features(crop, mask, bbox_info)
t2 = time.perf_counter()

grid_dict = engine.stage3.optimize_cylinder_grid(
    crop.shape,
    features["text_lines"],
    features["line_segments"],
    features["camera_params"],
    mask=mask,
    label_boundaries=features.get("label_boundaries")
)
t3 = time.perf_counter()

map_x, map_y = engine.stage4.compute_dense_backward_map(
    grid_dict["src_mesh_points"],
    grid_dict["dst_mesh_points"],
    (grid_dict["output_height"], grid_dict["output_width"])
)
t4 = time.perf_counter()

flat_img = engine.stage4.remap_lanczos(crop, map_x, map_y)
t5 = time.perf_counter()

post_img = engine.stage4.postprocess_orthographic_scan(flat_img)
t6 = time.perf_counter()

ocr_res = engine.stage5.process(post_img)
t7 = time.perf_counter()

print("========================================")
print("PERFORMANCE PROFILING BREAKDOWN:")
print(f"  Stage 1 (YOLO + SAM + Axis Derotation): {(t1 - t0)*1000:.1f} ms")
print(f"  Stage 2 (Vectorizer & Semi-Ellipse):    {(t2 - t1)*1000:.1f} ms")
print(f"  Stage 3 (Coon's Patch Grid Generation): {(t3 - t2)*1000:.1f} ms")
print(f"  Stage 4a (TPS RBF Coordinate Solving):  {(t4 - t3)*1000:.1f} ms")
print(f"  Stage 4b (cv2.remap Lanczos-4):          {(t5 - t4)*1000:.1f} ms")
print(f"  Stage 4c (Unsharp & CLAHE):             {(t6 - t5)*1000:.1f} ms")
print(f"  Stage 5 (Hybrid OCR GPU):               {(t7 - t6)*1000:.1f} ms")
print(f"  TOTAL TIME:                             {(t7 - t0)*1000:.1f} ms")
print("========================================")
