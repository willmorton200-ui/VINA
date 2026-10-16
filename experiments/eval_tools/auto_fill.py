import json
import os
import requests

EVAL_DIR = "D:/Eval"
MAPPING_FILE = os.path.join(EVAL_DIR, "mapping.json")

def main():
    if not os.path.exists(MAPPING_FILE):
        print(f"Файл {MAPPING_FILE} не найден!")
        return

    with open(MAPPING_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    updated = 0
    for case in data.get('cases', []):
        q_id = case.get('query_id', '')
        
        # Обрабатываем все пустые поля в датасете
        if q_id and not case.get('expected_slug'):
            try:
                num = int(q_id.split('-')[1])
            except:
                continue
                
            img_name = f"eval_photo_{num:03d}.webp"
            img_path = os.path.join(EVAL_DIR, "queries", img_name)
            
            if not os.path.exists(img_path):
                continue
                
            print(f"Анализируем {img_name}...")
            try:
                with open(img_path, 'rb') as img_f:
                    files = {'image': (img_name, img_f, 'image/webp')}
                    r = requests.post('http://127.0.0.1:8080/v1/eval/predict', files=files, timeout=60)
                    
                res = r.json()
                slug = res.get('slug')
                conf = res.get('confidence_percent', 0)
                
                if slug and conf > 85.0:
                    print(f"  -> Найдено: {slug} ({conf}%)")
                    case['expected_slug'] = slug
                    updated += 1
                else:
                    print(f"  -> Не уверен (Confidence {conf}%), пропускаю")
            except Exception as e:
                print(f"  -> Ошибка: {e}")

    if updated > 0:
        with open(MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nГотово! Успешно заполнено {updated} вин.")
        print("Не забудьте обновить страницу eval_editor, чтобы увидеть изменения!")
    else:
        print("\nНовых уверенных совпадений не найдено.")

if __name__ == '__main__':
    main()
