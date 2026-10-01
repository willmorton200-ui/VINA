
import csv
import os
import glob
import re

class WineCatalog:
    def __init__(self, csv_path: str = None, uploads_dir: str = None):
        """
        Инициализация каталога вин.
        Приоритет:
          1. wines_integrated_clean.csv + wines_images_clean/wines_images/ (новая база, 2103 вина)
          2. products_catalog.json + wines_integrated.csv + media/products/ (старая база, 2037 вин)
          3. strapi_output0709.csv + uploads/ (legacy)
        """
        # Пути к новой базе (приоритет №1)
        self.new_csv = csv_path or r"D:\VINA\wines_integrated_clean.csv"
        self.new_images_dir = uploads_dir or r"D:\VINA\wines_images_clean\wines_images"

        # Пути к старой базе (фоллбэк)
        self.old_json = r"D:\VINA\data\products_catalog.json"
        self.old_csv = r"D:\VINA\data\wines_integrated.csv"
        self.old_media = r"D:\VINA\media\products"

        # Пути к legacy (фоллбэк №2)
        self.legacy_csv = r"D:\VINA\TZ\Датасет\Датасет\strapi_output0709.csv"
        self.legacy_uploads = r"D:\VINA\TZ\Датасет\Датасет\prod-svoe-vino-strapi\prod-svoe-vino\strapi\uploads"

        self.wines_by_slug = {}
        self.upload_files = {}

        # Определяем, какую базу использовать
        if os.path.isfile(self.new_csv) and os.path.isdir(self.new_images_dir):
            self._load_clean_catalog()
        elif os.path.isfile(self.old_json) and os.path.isdir(self.old_media):
            self._load_full_catalog()
        else:
            self._index_uploads()
            self._load_legacy_catalog()

    def _load_clean_catalog(self):
        """Загрузка новой чистой базы: wines_integrated_clean.csv + wines_images_clean/"""
        print(f"[WineCatalog] Загрузка новой базы из {self.new_csv}...")
        
        wines_count = 0
        with_images = 0
        
        with open(self.new_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row in reader:
                if len(row) < 9:
                    continue
                
                slug = row[7].strip()
                if not slug:
                    continue
                
                photo_name = row[10].strip() if len(row) > 10 and row[10].strip() else (row[8].strip() if len(row) > 8 else "")
                # Путь к картинке в новой папке
                image_path = os.path.join(self.new_images_dir, photo_name) if photo_name else ""
                
                sweetness = ""
                if "-polusuhoe" in slug: sweetness = "полусухое"
                elif "-suhoe" in slug: sweetness = "сухое"
                elif "-polusladkoe" in slug: sweetness = "полусладкое"
                elif "-sladkoe" in slug: sweetness = "сладкое"
                elif "-desertnoe" in slug: sweetness = "десертное"
                
                self.wines_by_slug[slug] = {
                    "name": row[0].strip(),
                    "category": row[1].strip(),
                    "sweetness": sweetness,
                    "color": row[2].strip(),
                    "region": row[3].strip(),
                    "grape": row[4].strip(),
                    "description": row[5].strip(),
                    "winery": row[6].strip(),
                    "slug": slug,
                    "photo_name": photo_name,
                    "image_path": image_path if os.path.isfile(image_path) else "",
                }
                
                wines_count += 1
                if self.wines_by_slug[slug]["image_path"]:
                    with_images += 1
        
        print(f"[WineCatalog] Новая база: {wines_count} вин, {with_images} с изображениями")

    def _load_full_catalog(self):
        """Загрузка старой полной базы: products_catalog.json + wines_integrated.csv"""
        print(f"[WineCatalog] Загрузка старой базы из {self.old_json}...")
        import json
        with open(self.old_json, "r", encoding="utf-8") as f:
            products = json.load(f)

        df_by_slug = {}
        if os.path.isfile(self.old_csv):
            try:
                import pandas as pd
                df = pd.read_csv(self.old_csv)
                df_by_slug = {r['Slug']: r for _, r in df.iterrows() if pd.notna(r.get('Slug'))}
            except Exception as e:
                print(f"[WineCatalog] Предупреждение при чтении {self.old_csv}: {e}")

        for p in products:
            slug = p.get("slug")
            if not slug:
                continue

            extra = df_by_slug.get(slug, {})
            prod_id = p.get("id")
            src_path = os.path.join(self.old_media, prod_id, "source.webp")
            lbl_path = os.path.join(self.old_media, prod_id, "label.webp")

            self.wines_by_slug[slug] = {
                "name": str(extra.get("Название вина") or p.get("title") or slug),
                "winery": str(extra.get("Винодельня") or p.get("manufacturer") or ""),
                "category": str(extra.get("Категория") or ""),
                "color": str(extra.get("Цвет") or ""),
                "region": str(extra.get("Регион") or ""),
                "grape": str(extra.get("Сорт винограда") or ""),
                "description": str(extra.get("Описание") or p.get("description") or ""),
                "slug": slug,
                "image_path": src_path if os.path.isfile(src_path) else "",
                "label_path": lbl_path if os.path.isfile(lbl_path) else "",
            }

        print(f"[WineCatalog] Старая база: {len(self.wines_by_slug)} вин загружено")

    def _index_uploads(self):
        if not os.path.exists(self.legacy_uploads):
            return
        for root, _, files in os.walk(self.legacy_uploads):
            for file in files:
                if file.lower().endswith(('.webp', '.png', '.jpg', '.jpeg')):
                    if file.startswith(('thumbnail_', 'small_', 'medium_', 'large_')):
                        continue
                    self.upload_files[file] = os.path.join(root, file)

    def _clean_str(self, s: str) -> str:
        return re.sub(r'[^a-z0-9]', '', s.lower())

    def _find_image_path(self, photo_name: str, slug: str) -> str:
        if not photo_name:
            return ""
        if photo_name in self.upload_files:
            return self.upload_files[photo_name]
        name_without_ext = os.path.splitext(photo_name)[0]
        for file_name, full_path in self.upload_files.items():
            if file_name.startswith(name_without_ext):
                return full_path
        for file_name, full_path in self.upload_files.items():
            if file_name.startswith(slug) or file_name.startswith(slug.replace('-', '_')):
                return full_path
        clean_slug = self._clean_str(slug)
        for file_name, full_path in self.upload_files.items():
            clean_file = self._clean_str(os.path.splitext(file_name)[0])
            if clean_file[:-10] == clean_slug or clean_slug in clean_file:
                return full_path
        return ""

    def _load_legacy_catalog(self):
        if not os.path.exists(self.legacy_csv):
            return
        with open(self.legacy_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            for row in reader:
                if len(row) < 9:
                    continue
                slug = row[7].strip()
                if not slug:
                    continue
                photo_name = row[8].strip()
                image_path = self._find_image_path(photo_name, slug)
                self.wines_by_slug[slug] = {
                    "name": row[0].strip(),
                    "category": row[1].strip(),
                    "color": row[2].strip(),
                    "region": row[3].strip(),
                    "grape": row[4].strip(),
                    "description": row[5].strip(),
                    "winery": row[6].strip(),
                    "slug": slug,
                    "photo_name_csv": photo_name,
                    "image_path": image_path
                }

    def get_wine(self, slug: str) -> dict:
        return self.wines_by_slug.get(slug)

    def get_all_wines(self) -> list:
        return list(self.wines_by_slug.values())

    def get_wines_with_images(self) -> list:
        return [w for w in self.wines_by_slug.values() if w.get("image_path")]
