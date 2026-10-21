
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
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent

        self.new_csv = csv_path
        if not self.new_csv:
            csv_candidate = base_dir / "wines_integrated_clean.csv"
            self.new_csv = str(csv_candidate) if csv_candidate.exists() else str(Path(r"D:\VINA\wines_integrated_clean.csv"))
            
        self.new_images_dir = uploads_dir
        if not self.new_images_dir:
            img_candidate = base_dir / "wines_images_clean" / "wines_images"
            self.new_images_dir = str(img_candidate) if img_candidate.exists() else str(Path(r"D:\VINA\wines_images_clean\wines_images"))

        # Пути к старой базе (фоллбэк)
        self.old_json = str(base_dir / "data" / "products_catalog.json")
        self.old_csv = str(base_dir / "data" / "wines_integrated.csv")
        self.old_media = str(base_dir / "media" / "products")

        # Пути к legacy (фоллбэк №2)
        self.legacy_csv = str(base_dir / "TZ" / "Датасет" / "Датасет" / "strapi_output0709.csv")
        self.legacy_uploads = str(base_dir / "TZ" / "Датасет" / "Датасет" / "prod-svoe-vino-strapi" / "prod-svoe-vino" / "strapi" / "uploads")

        self.wines_by_slug = {}
        self.upload_files = {}

        # Определяем, какую базу использовать
        if os.path.isfile(self.new_csv):
            self._load_clean_catalog()
        elif os.path.isfile(self.old_json) and os.path.isdir(self.old_media):
            self._load_full_catalog()
        elif os.path.isfile(self.legacy_csv):
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
                if image_path and not os.path.isfile(image_path):
                    stem, _ = os.path.splitext(image_path)
                    for alt_ext in [".webp", ".jpg", ".png", ".jpeg"]:
                        if os.path.isfile(stem + alt_ext):
                            image_path = stem + alt_ext
                            photo_name = os.path.basename(image_path)
                            break
                
                # Поле sweetness используется в HybridRanker (строго по ключам SWEETNESS_ONTOLOGY / слагам)
                sweetness = ""
                if "-polusuhoe" in slug:
                    sweetness = "полусухое"
                elif "-suhoe" in slug:
                    sweetness = "сухое"
                elif "-polusladkoe" in slug:
                    sweetness = "полусладкое"
                elif "-sladkoe" in slug:
                    sweetness = "сладкое"
                elif "-desertnoe" in slug:
                    sweetness = "десертное"

                # Поле sugar используется только для отображения и фильтрации в UI-каталоге (/api/v2/catalog)
                title_cat = f"{row[0].lower()} {row[1].lower()}"
                sugar = sweetness
                if not sugar:
                    if "-bryut" in slug or "bryut" in slug.lower() or "брют" in title_cat or "brut" in title_cat:
                        sugar = "брют"
                    elif "полусух" in title_cat or "semi-dry" in title_cat:
                        sugar = "полусухое"
                    elif "полуслад" in title_cat or "semi-sweet" in title_cat:
                        sugar = "полусладкое"
                    elif "десерт" in title_cat or "ликерн" in title_cat:
                        sugar = "десертное"
                    elif "сладк" in title_cat:
                        sugar = "сладкое"
                    elif "сух" in title_cat:
                        sugar = "сухое"

                alcohol = ""
                alc_match = re.search(r"-(\d{2,3})$", slug)
                if alc_match:
                    val = alc_match.group(1)
                    alcohol = f"{val[:2]}.{val[2]}%" if len(val) == 3 else f"{val}%"
                if not alcohol:
                    alcohol = "16.0%" if ("портвейн" in slug or "мадера" in slug or "ликер" in row[1].lower()) else "13.0%"

                remote_image_url = row[13].strip() if len(row) > 13 else ""
                page_url = row[9].strip() if len(row) > 9 else ""
                xml_photo = row[12].strip() if len(row) > 12 else ""

                self.wines_by_slug[slug] = {
                    "name": row[0].strip(),
                    "category": row[1].strip(),
                    "sweetness": sweetness,
                    "sugar": sugar,
                    "color": row[2].strip(),
                    "region": row[3].strip(),
                    "grape": row[4].strip(),
                    "description": row[5].strip(),
                    "winery": row[6].strip(),
                    "slug": slug,
                    "photo_name": photo_name,
                    "image_path": image_path if os.path.isfile(image_path) else "",
                    "remote_image_url": remote_image_url,
                    "image_url": remote_image_url,
                    "page_url": page_url,
                    "xml_photo": xml_photo,
                    "alcohol": alcohol,
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
