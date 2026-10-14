import os
import torch
import numpy as np
import faiss
import open_clip
from PIL import Image
import cv2
import pickle
import time

class WineSearchEngine:
    def __init__(self, catalog, use_gpu: bool = True, index_path: str = None):
        """
        Поисковый движок на базе SigLIP 2 и FAISS.
        """
        if index_path is None:
            from pathlib import Path
            index_path = str(Path(__file__).resolve().parent.parent / "models" / "siglip2_index.faiss")
        self.catalog = catalog
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.device = "cuda:0" if self.use_gpu else "cpu"
        self.index_path = index_path
        self.model_name = "ViT-B-16-SigLIP2-384"
        self.pretrained = "webli"
        
        print(f"[SearchEngine] Загрузка модели {self.model_name} на {self.device}...")
        t0 = time.time()
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            self.model_name, 
            pretrained=self.pretrained, 
            device=self.device
        )
        self.model.eval()
        print(f"[SearchEngine] Модель загружена за {time.time()-t0:.1f}с")
        
        self.index = None
        self.slugs = []  # Маппинг id в faiss -> slug вина
        self.meta_path = self.index_path.replace('.faiss', '_meta.pkl')
        
        # Попытка загрузить существующий индекс
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            self._load_index()
        else:
            self._build_index()

    def get_embedding(self, image: Image.Image) -> np.ndarray:
        """Получение L2-нормализованного вектора изображения."""
        img_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad(), torch.cuda.amp.autocast(enabled=self.use_gpu):
            features = self.model.encode_image(img_tensor)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy().astype(np.float32)

    def _build_index(self):
        """Проходит по каталогу, извлекает embeddings и строит FAISS индекс."""
        print("[SearchEngine] Построение FAISS индекса...")
        wines = self.catalog.get_wines_with_images()
        if not wines:
            print("[SearchEngine] В каталоге нет вин с изображениями!")
            return
            
        embeddings = []
        self.slugs = []
        
        for idx, wine in enumerate(wines):
            try:
                img = Image.open(wine["image_path"]).convert("RGB")
                emb = self.get_embedding(img)
                embeddings.append(emb[0])
                self.slugs.append(wine["slug"])
                
                if (idx + 1) % 100 == 0:
                    print(f"  Обработано {idx+1}/{len(wines)} изображений...")
            except Exception as e:
                print(f"[SearchEngine] Ошибка при обработке {wine['image_path']}: {e}")
                
        if not embeddings:
            return
            
        emb_matrix = np.vstack(embeddings)
        d = emb_matrix.shape[1]
        
        # Используем Inner Product (Cosine similarity так как векторы L2-нормализованы)
        self.index = faiss.IndexFlatIP(d)
        self.index.add(emb_matrix)
        print(f"[SearchEngine] Индекс построен. Векторов: {self.index.ntotal}, размерность: {d}")
        
        # Сохранение
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, 'wb') as f:
            pickle.dump(self.slugs, f)

    def _load_index(self):
        # Загружает сохраненный индекс FAISS.
        print(f"[SearchEngine] Загрузка FAISS индекса из {self.index_path}...")
        self.index = faiss.read_index(self.index_path)
            
        with open(self.meta_path, 'rb') as f:
            self.slugs = pickle.load(f)
        print(f"[SearchEngine] Индекс загружен (размер: {self.index.ntotal}).")

    def search_by_cv2_image(self, bgr_img: np.ndarray, top_k: int = 5):
        # Returns list of dicts with slug, score, wine_data
        if self.index is None or self.index.ntotal == 0:
            return []
            
        rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        emb = self.get_embedding(pil_img)
        
        # FAISS search (запрашиваем с запасом для дедупликации вин с несколькими векторами)
        k_search = min(top_k * 4, self.index.ntotal)
        scores, indices = self.index.search(emb, k_search)

        results = []
        seen_slugs = set()

        for i in range(k_search):
            idx = indices[0][i]
            score = float(scores[0][i])
            if idx < 0 or idx >= len(self.slugs):
                continue

            slug = self.slugs[idx]
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            wine_data = self.catalog.get_wine(slug)
            results.append({
                "slug": slug,
                "score": score,  # Cosine similarity (-1 to 1)
                "wine_data": wine_data
            })

            if len(results) >= top_k:
                break

        return results

    def search_by_text(self, ocr_text: str, top_k: int = 20):
        # Text-based fallback using OCR and transliteration
        if not ocr_text or not str(ocr_text).strip():
            return []
            
        import re
        from pipeline.vina_studio_matcher import extract_ocr_words, extract_slug_words
        
        ocr_words = extract_ocr_words(ocr_text)
        if not ocr_words:
            return []
            
        results = []
        for wine in self.catalog.get_all_wines():
            slug = wine.get("slug", "")
            name = wine.get("name", "") or wine.get("title", "")
            winery = wine.get("winery", "")
            
            slug_words = extract_slug_words(slug)
            
            # Words from name and winery (split by non-alphanumeric)
            name_words = set(w.upper() for w in re.findall(r'[A-Za-zА-Яа-яЁё0-9]+', name))
            winery_words = set(w.upper() for w in re.findall(r'[A-Za-zА-Яа-яЁё0-9]+', winery))
            
            target_words = set(slug_words).union(name_words).union(winery_words)
            
            # Raw number of intersecting words (weighting longer words slightly higher)
            intersection = target_words.intersection(ocr_words)
            score = sum(len(w) for w in intersection)
            
            if score > 0:
                results.append({
                    "slug": slug,
                    "score": score,
                    "wine_data": wine
                })
                
        results.sort(key=lambda x: x["score"], reverse=True)
        # Normalize scores to 0-1 range to roughly mimic cosine similarity
        if results and results[0]["score"] > 0:
            max_score = results[0]["score"]
            for r in results:
                # Text scores aren't exactly equivalent to SigLIP scores (which are -1 to 1)
                # But we map them to 0.5 - 0.9 range so they get evaluated in cascade
                r["score"] = 0.5 + 0.4 * (r["score"] / max_score)
        
        return results[:top_k]
