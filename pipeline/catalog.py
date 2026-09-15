import csv
import os
import glob
import re

class WineCatalog:
    def __init__(self, csv_path: str, uploads_dir: str):
        """
        Инициализация каталога вин.
        :param csv_path: Путь до CSV дампа
        :param uploads_dir: Путь до папки uploads с картинками
        """
        self.csv_path = csv_path
        self.uploads_dir = uploads_dir
        self.wines_by_slug = {}
        
        self.upload_files = {}
        self._index_uploads()
        self._load_catalog()

    def _index_uploads(self):
        if not os.path.exists(self.uploads_dir):
            print(f"[WineCatalog] Внимание: папка {self.uploads_dir} не найдена.")
            return
            
        print(f"[WineCatalog] Индексация изображений в {self.uploads_dir}...")
        for root, _, files in os.walk(self.uploads_dir):
            for file in files:
                if file.lower().endswith(('.webp', '.png', '.jpg', '.jpeg')):
                    # Игнорируем уменьшенные копии Strapi, нам нужен оригинал
                    if file.startswith(('thumbnail_', 'small_', 'medium_', 'large_')):
                        continue
                    self.upload_files[file] = os.path.join(root, file)
        
        print(f"[WineCatalog] Найдено {len(self.upload_files)} оригинальных изображений.")

    def _clean_str(self, s: str) -> str:
        return re.sub(r'[^a-z0-9]', '', s.lower())

    def _find_image_path(self, photo_name: str, slug: str) -> str:
        if not photo_name:
            return ""
            
        if photo_name in self.upload_files:
            return self.upload_files[photo_name]
            
        name_without_ext = os.path.splitext(photo_name)[0]
        
        # 1. По началу имени из CSV
        for file_name, full_path in self.upload_files.items():
            if file_name.startswith(name_without_ext):
                return full_path
                
        # 2. По slug (Strapi часто называет файлы так же, как slug)
        for file_name, full_path in self.upload_files.items():
            if file_name.startswith(slug) or file_name.startswith(slug.replace('-', '_')):
                return full_path
                
        # 3. Fuzzy search по очищенному имени
        clean_slug = self._clean_str(slug)
        for file_name, full_path in self.upload_files.items():
            clean_file = self._clean_str(os.path.splitext(file_name)[0])
            # Отрезаем хеш Strapi (последние 10 символов)
            if clean_file[:-10] == clean_slug or clean_slug in clean_file:
                return full_path
                
        return ""

    def _load_catalog(self):
        if not os.path.exists(self.csv_path):
            print(f"[WineCatalog] Ошибка: CSV файл {self.csv_path} не найден.")
            return
            
        print(f"[WineCatalog] Загрузка каталога из {self.csv_path}...")
        with open(self.csv_path, 'r', encoding='utf-8') as f:
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
                
        print(f"[WineCatalog] Загружено {len(self.wines_by_slug)} уникальных вин.")

    def get_wine(self, slug: str) -> dict:
        return self.wines_by_slug.get(slug)

    def get_all_wines(self) -> list:
        return list(self.wines_by_slug.values())

    def get_wines_with_images(self) -> list:
        return [w for w in self.wines_by_slug.values() if w["image_path"]]

if __name__ == "__main__":
    csv_file = r"D:\VINA\TZ\Датасет\Датасет\strapi_output0709.csv"
    uploads = r"D:\VINA\TZ\Датасет\Датасет\prod-svoe-vino-strapi\prod-svoe-vino\strapi\uploads"
    
    catalog = WineCatalog(csv_file, uploads)
    
    with_img = catalog.get_wines_with_images()
    print(f"Вин с найденными фото: {len(with_img)}")
