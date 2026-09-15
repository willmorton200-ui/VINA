import re
import difflib

# Demonstration of Context-Aware Language Detection & Optical Transliteration

def detect_label_language(tokens):
    """
    Analyzes recognized tokens to determine dominant language (Russian vs Latin).
    """
    ru_chars = sum(len(re.findall(r'[а-яА-ЯёЁ]', t)) for t in tokens)
    en_chars = sum(len(re.findall(r'[a-zA-Z]', t)) for t in tokens)
    
    # Also check presence of unambiguous Russian marker tokens
    ru_markers = {"ПОЛУСУХОЕ", "КРАСНОЕ", "МОНАСТЫРСКАЯ", "ИЗБА", "ОБЪЕМ", "СУХОЕ", "БЕЛОЕ", "РОССИЯ", "САПЕРАВИ"}
    has_ru_marker = any(t.upper() in ru_markers for t in tokens)
    
    if has_ru_marker or ru_chars >= 5:
        return "ru"
    return "en"

# Optical Homoglyph Matrix: maps Latin OCR misrecognitions back to Cyrillic
HOMOGLYPH_LATIN_TO_CYRILLIC = {
    'B': 'В', 'H': 'Н', 'N': 'И', 'P': 'Р', 'C': 'С', 'Y': 'У', 
    'X': 'Х', 'O': 'О', 'E': 'Е', 'A': 'А', 'K': 'К', 'M': 'М', 'T': 'Т',
    'I': 'Г', 'S': 'Ь', 'b': 'Ь', '0': 'О', '3': 'З', '6': 'Б'
}

def transliterate_optical_confusables(word: str) -> str:
    res = []
    w = word.upper()
    i = 0
    while i < len(w):
        # 2-char ligatures
        if i + 1 < len(w) and w[i:i+2] == "NH":  # 'NH' -> 'И'
            res.append('И')
            i += 2
        elif i + 1 < len(w) and w[i:i+2] == "IP": # 'IP' -> 'ГР'
            res.append('ГР')
            i += 2
        elif i + 1 < len(w) and w[i:i+2] == "AA": # 'AA' -> 'АД'
            res.append('АД')
            i += 2
        elif i + 1 < len(w) and w[i:i+2] == "IS": # 'IS' -> 'ЛЬ'
            res.append('ЛЬ')
            i += 2
        else:
            ch = w[i]
            res.append(HOMOGLYPH_LATIN_TO_CYRILLIC.get(ch, ch))
            i += 1
    return "".join(res)

test_phrase = "BNHO BHHOIPAAHOEHATYPAISHOE"
words = test_phrase.split()

dictionary = [
    "ВИНО", "ВИНОГРАДНОЕ", "НАТУРАЛЬНОЕ", "ВИНО ВИНОГРАДНОЕ НАТУРАЛЬНОЕ",
    "ПОЛУСУХОЕ", "КРАСНОЕ", "МОНАСТЫРСКАЯ ИЗБА", "ОБЪЕМ"
]

print(f"Original Raw OCR: '{test_phrase}'")
for w in words:
    # 1. Direct match check
    # 2. Transliterated candidate
    cyr_cand = transliterate_optical_confusables(w)
    # 3. Fuzzy search in Russian Wine Lexicon
    matches = difflib.get_close_matches(cyr_cand, dictionary, n=1, cutoff=0.55)
    print(f"  Token: '{w}' -> Optical Cyrillic: '{cyr_cand}' -> Dictionary Match: {matches}")
