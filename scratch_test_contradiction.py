import csv
from pipeline.vina_studio_matcher import check_color_contradiction, extract_ocr_words

def check_catalog():
    csv_path = r"D:\VINA\wines_integrated_clean.csv"
    false_positives = 0
    total = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if len(row) < 9: continue
            slug = row[7].strip()
            name = row[0].strip()
            category = row[1].strip()
            
            # Представим, что OCR идеально прочитал название и сорта винограда
            ocr_text = name + " " + row[4].strip() # name + grape
            ocr_words = extract_ocr_words(ocr_text)
            
            wine_info = {"category": category, "name": name}
            
            if check_color_contradiction(ocr_words, slug, wine_info):
                false_positives += 1
                print(f"ЛОЖНЫЙ ШТРАФ: {slug} | Cat: {category} | OCR_TEXT: {ocr_text} | OCR_WORDS: {ocr_words}")
            
            total += 1
            
    print(f"Total checked: {total}")
    print(f"False positive penalties: {false_positives} ({(false_positives/total)*100:.2f}%)")

if __name__ == "__main__":
    check_catalog()
