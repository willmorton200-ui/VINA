"""
DINOv2-small + LoRA поисковый движок (архитектура заимствована из D:\\VINA2\\lct2026prod).
Индекс строится по КРОПАМ ЭТИКЕТОК каталожных фото (так модель обучалась в VINA2).
Кроп этикетки делается одной и той же функцией для каталога и для запроса.
"""
import os
import pickle
import time
from pathlib import Path

import cv2
import faiss
import numpy as np
import torch
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
VINA2_MODELS = Path(r"D:\VINA2\lct2026prod\models")

NEW_TRAINED_LORA = MODELS_DIR / "dinov2_lora_all_wines"
DINO_LORA_PATH = NEW_TRAINED_LORA if NEW_TRAINED_LORA.exists() else (VINA2_MODELS / "dinov2_label_finetuned")

if (MODELS_DIR / "dinov2-small").exists():
    DINO_BASE_PATH = MODELS_DIR / "dinov2-small"
elif VINA2_MODELS.exists() and (VINA2_MODELS / "dinov2-small").exists():
    DINO_BASE_PATH = VINA2_MODELS / "dinov2-small"
else:
    DINO_BASE_PATH = "facebook/dinov2-small"

YOLO_V2_PATH = MODELS_DIR / "best_v2_100bottles.pt"
DEFAULT_INDEX = MODELS_DIR / "dino_all_wines_index.faiss"


class DinoLabelEngine:
    def __init__(self, catalog, use_gpu: bool = True, index_path: Path = DEFAULT_INDEX, yolo_model=None):
        from transformers import AutoImageProcessor, AutoModel
        self.catalog = catalog
        self.device = "cuda:0" if use_gpu and torch.cuda.is_available() else "cpu"
        t0 = time.time()
        proc_path = str(DINO_BASE_PATH)
        is_local = os.path.exists(proc_path)
        self.processor = AutoImageProcessor.from_pretrained(proc_path, local_files_only=is_local, use_fast=False)
        base = AutoModel.from_pretrained(proc_path, local_files_only=is_local)
        if DINO_LORA_PATH.exists() and ((DINO_LORA_PATH / "adapter_model.bin").exists() or (DINO_LORA_PATH / "adapter_config.json").exists() or (DINO_LORA_PATH / "adapter_model.safetensors").exists()):
            from peft import PeftModel
            try:
                self.model = PeftModel.from_pretrained(base, str(DINO_LORA_PATH), local_files_only=True)
                print(f"[DINO] Full-Catalog LoRA adapter ({DINO_LORA_PATH.name}) loaded via PeftModel.")
            except Exception:
                from peft import LoraConfig, get_peft_model
                lora_cfg = LoraConfig(
                    r=16,
                    lora_alpha=32,
                    target_modules=["query", "key", "value", "dense"],
                    lora_dropout=0.05,
                    bias="none"
                )
                self.model = get_peft_model(base, lora_cfg)
                safe_file = DINO_LORA_PATH / "adapter_model.safetensors"
                bin_file = DINO_LORA_PATH / "adapter_model.bin"
                if safe_file.exists():
                    from safetensors.torch import load_file
                    state = load_file(str(safe_file))
                else:
                    state = torch.load(str(bin_file), map_location="cpu")
                self.model.load_state_dict(state, strict=False)
                print(f"[DINO] Full-Catalog LoRA adapter applied successfully.")
        else:
            self.model = base
        self.model = self.model.to(self.device).eval()
        print(f"[DINO] DINOv2+LoRA загружен за {time.time() - t0:.1f}с на {self.device}")

        if yolo_model is None:
            from ultralytics import YOLO
            yolo_model = YOLO(str(YOLO_V2_PATH))
        self.yolo = yolo_model

        self.index_path = Path(index_path)
        self.meta_path = Path(str(self.index_path).replace(".faiss", "_meta.pkl"))
        self.index, self.slugs = None, []
        if self.index_path.exists() and self.meta_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.meta_path, "rb") as f:
                self.slugs = pickle.load(f)
            print(f"[DINO] Индекс загружен: {self.index.ntotal} векторов")
        else:
            self.build_index()

    # --- Кроп этикетки: единая функция для каталога и запроса ---
    def crop_label(self, bgr: np.ndarray) -> np.ndarray:
        h, w = bgr.shape[:2]
        try:
            r = self.yolo.predict(bgr, verbose=False, conf=0.25, device=self.device)[0]
            best, best_area = None, 0
            for b, c in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.cls.cpu().numpy()):
                if int(c) != 0:
                    continue
                x1, y1, x2, y2 = [int(v) for v in b]
                # исключаем «этикетку» во весь кадр от верхнего края (это тело бутылки)
                if (y2 - y1) >= 0.70 * h and y1 <= 0.10 * h:
                    continue
                area = (x2 - x1) * (y2 - y1)
                if area > best_area:
                    best, best_area = (x1, y1, x2, y2), area
            if best is not None:
                x1, y1, x2, y2 = best
                return bgr[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        except Exception as e:
            print(f"[DINO] crop_label warning: {e}")
        return bgr

    @torch.no_grad()
    def embed_bgr(self, bgr_list):
        imgs = [Image.fromarray(cv2.cvtColor(b, cv2.COLOR_BGR2RGB)) for b in bgr_list]
        px = self.processor(images=imgs, return_tensors="pt")["pixel_values"].to(self.device)
        out = self.model(px)
        feats = out.pooler_output if getattr(out, "pooler_output", None) is not None else out.last_hidden_state[:, 0, :]
        return torch.nn.functional.normalize(feats, dim=-1).cpu().numpy().astype(np.float32)

    def build_index(self):
        wines = self.catalog.get_wines_with_images()
        print(f"[DINO] Построение индекса по кропам этикеток: {len(wines)} фото...")
        embs, slugs, batch, batch_slugs = [], [], [], []
        for i, wine in enumerate(wines):
            bgr = cv2.imread(wine["image_path"])
            if bgr is None:
                pil = Image.open(wine["image_path"]).convert("RGB")
                bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
            batch.append(self.crop_label(bgr))
            batch_slugs.append(wine["slug"])
            if len(batch) == 32 or i == len(wines) - 1:
                embs.append(self.embed_bgr(batch))
                slugs.extend(batch_slugs)
                batch, batch_slugs = [], []
            if (i + 1) % 200 == 0:
                print(f"  {i + 1}/{len(wines)}")
        mat = np.vstack(embs)
        self.index = faiss.IndexFlatIP(mat.shape[1])
        self.index.add(mat)
        self.slugs = slugs
        faiss.write_index(self.index, str(self.index_path))
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.slugs, f)
        print(f"[DINO] Индекс сохранён: {self.index.ntotal} векторов, dim={mat.shape[1]}")

    def search_by_cv2_image(self, bgr: np.ndarray, top_k: int = 20):
        emb = self.embed_bgr([self.crop_label(bgr)])
        k = min(top_k * 3, self.index.ntotal)
        scores, idx = self.index.search(emb, k)
        res, seen = [], set()
        for s, i in zip(scores[0], idx[0]):
            if i < 0:
                continue
            slug = self.slugs[i]
            if slug in seen:
                continue
            seen.add(slug)
            res.append({"slug": slug, "score": float(s), "wine_data": self.catalog.get_wine(slug)})
            if len(res) >= top_k:
                break
        return res
