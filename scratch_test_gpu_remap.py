import time
import cv2
import numpy as np
import torch
import torch.nn.functional as F

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print(f"Testing GPU Remap on device: {device} ({torch.cuda.get_device_name(0)})")

# Load high-res crop
img_bgr = cv2.imread("test_dataset/butilki/photo_2026-08-10_12-34-31.jpg")
h, w = img_bgr.shape[:2]
out_h, out_w = 800, 600

# Generate a sample 3D Coon's patch grid (e.g. 31x31 control grid)
grid_rows, grid_cols = 31, 31
src_u = np.linspace(50, w - 50, grid_cols)
src_v = np.linspace(100, h - 100, grid_rows)
src_grid_x, src_grid_y = np.meshgrid(src_u, src_v)
# Add cylinder curvature
src_grid_y += 30 * np.sin(np.linspace(0, np.pi, grid_cols))[None, :]

# ----------------------------------------------------
# Method 1: CPU Scipy RBF + cv2.remap (Old method)
# ----------------------------------------------------
from scipy.interpolate import RBFInterpolator

t0 = time.perf_counter()
eval_h, eval_w = 256, 256
dst_pts = np.column_stack((np.linspace(0, out_w-1, grid_cols*grid_rows), np.linspace(0, out_h-1, grid_cols*grid_rows)))
src_pts = np.column_stack((src_grid_x.ravel(), src_grid_y.ravel()))

grid_y_eval, grid_x_eval = np.meshgrid(np.linspace(0, out_h-1, eval_h), np.linspace(0, out_w-1, eval_w), indexing='ij')
eval_pts = np.column_stack((grid_x_eval.ravel(), grid_y_eval.ravel()))

rbf_u = RBFInterpolator(np.column_stack((np.repeat(np.linspace(0, out_w-1, grid_cols), grid_rows), np.tile(np.linspace(0, out_h-1, grid_rows), grid_cols))), src_pts[:, 0], kernel='thin_plate_spline')
map_u_c = rbf_u(eval_pts).reshape(eval_h, eval_w).astype(np.float32)
map_x_cpu = cv2.resize(map_u_c, (out_w, out_h), interpolation=cv2.INTER_CUBIC)
map_y_cpu = np.tile(np.linspace(0, h-1, out_h).reshape(-1, 1), (1, out_w)).astype(np.float32)
dewarped_cpu = cv2.remap(img_bgr, map_x_cpu, map_y_cpu, interpolation=cv2.INTER_LANCZOS4)
t_cpu = (time.perf_counter() - t0) * 1000
print(f"CPU Remap + RBF Time: {t_cpu:.1f} ms")

# ----------------------------------------------------
# Method 2: Pure GPU PyTorch Grid Transformation (NEW METHOD)
# ----------------------------------------------------
# Warmup CUDA
img_tensor = torch.from_numpy(img_bgr).permute(2, 0, 1).unsqueeze(0).float().to(device)
grid_x_t = torch.from_numpy(src_grid_x).unsqueeze(0).unsqueeze(0).float().to(device)
grid_y_t = torch.from_numpy(src_grid_y).unsqueeze(0).unsqueeze(0).float().to(device)

torch.cuda.synchronize()
t0 = time.perf_counter()

# 1. Upsample 31x31 Coon's patch grid to full (out_h, out_w) directly in GPU VRAM via bicubic
dense_grid_x = F.interpolate(grid_x_t, size=(out_h, out_w), mode='bicubic', align_corners=True)
dense_grid_y = F.interpolate(grid_y_t, size=(out_h, out_w), mode='bicubic', align_corners=True)

# 2. Normalize coordinates to [-1, 1] for torch grid_sample
norm_grid_x = 2.0 * (dense_grid_x / (w - 1.0)) - 1.0
norm_grid_y = 2.0 * (dense_grid_y / (h - 1.0)) - 1.0
grid_gpu = torch.stack((norm_grid_x.squeeze(), norm_grid_y.squeeze()), dim=-1).unsqueeze(0)

# 3. High-fidelity subpixel bicubic sampling on GPU
dewarped_tensor = F.grid_sample(img_tensor, grid_gpu, mode='bicubic', padding_mode='border', align_corners=True)
dewarped_gpu = dewarped_tensor.squeeze().permute(1, 2, 0).byte().cpu().numpy()

torch.cuda.synchronize()
t_gpu = (time.perf_counter() - t0) * 1000
print(f"GPU PyTorch CUDA Remap Time: {t_gpu:.2f} ms")
print(f"SPEEDUP: {t_cpu / t_gpu:.1f}x faster on GPU!")

cv2.imwrite("scratch_debug_gpu_remap.png", dewarped_gpu)
print("Saved scratch_debug_gpu_remap.png successfully!")
