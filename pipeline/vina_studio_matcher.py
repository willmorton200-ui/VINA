
"""
VINA STUDIO Cascade Matcher v4
================================
Формула уверенности:
  final = confidence_embedding + 100 / divisor

  divisor зависит от доли совпавших слов slug с OCR-текстом:
    1 → все слова совпали (≥90%)
    2 → половина слов совпала (≥50%)
    3 → треть слов совпала (≥33%)
    4 → < 1/3 слов совпало

Проверяем **топ-5** лучших результатов SigLIP.
"""

import re
from typing import List, Dict, Tuple


# --- Транслитерация ---
CYR_TO_LAT_MAP = {
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
    'Е': 'E', 'Ё': 'YO', 'Ж': 'ZH', 'З': 'Z', 'И': 'I',
    'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
    'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
    'У': 'U', 'Ф': 'F', 'Х': 'KH', 'Ц': 'TS', 'Ч': 'CH',
    'Ш': 'SH', 'Щ': 'SHCH', 'Ъ': '"', 'Ы': 'Y', 'Ь': "'",
    'Э': 'E', 'Ю': 'YU', 'Я': 'YA',
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
    'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
    'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
    'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
    'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'shch', 'ъ': '"', 'ы': 'y', 'ь': "'",
    'э': 'e', 'ю': 'yu', 'я': 'ya',
}

LAT_TO_CYR_MULTI = {
    'YO': 'Ё', 'ZH': 'Ж', 'KH': 'Х', 'TS': 'Ц', 'CH': 'Ч',
    'SH': 'Ш', 'SHCH': 'Щ', 'YU': 'Ю', 'YA': 'Я',
    'yo': 'ё', 'zh': 'ж', 'kh': 'х', 'ts': 'ц', 'ch': 'ч',
    'sh': 'ш', 'shch': 'щ', 'yu': 'ю', 'ya': 'я',
}
LAT_TO_CYR_MAP = {v: k for k, v in CYR_TO_LAT_MAP.items() if len(v) == 1}


def cyrillic_to_latin(text: str) -> str:
    return ''.join(CYR_TO_LAT_MAP.get(ch, ch) for ch in text)


def latin_to_cyrillic(text: str) -> str:
    result = []
    i = 0
    while i < len(text):
        found = False
        for pat_len in [4, 3, 2]:
            if i + pat_len <= len(text):
                sub = text[i:i+pat_len]
                if sub in LAT_TO_CYR_MULTI:
                    result.append(LAT_TO_CYR_MULTI[sub])
                    i += pat_len
                    found = True
                    break
        if not found:
            result.append(LAT_TO_CYR_MAP.get(text[i], text[i]))
            i += 1
    return ''.join(result)


def normalize_word(word: str) -> str:
    return re.sub(r'[^\w\s]', '', word).strip().upper()


def is_cyrillic(text: str) -> bool:
    return any('А' <= c <= 'Я' or c == 'Ё' or 'а' <= c <= 'я' or c == 'ё' for c in text)


def extract_slug_words(slug: str) -> List[str]:
    parts = slug.replace('_', '-').split('-')
    seen = set()
    words = []
    for part in parts:
        if not part or len(part) < 2:
            continue
        norm = part.upper()
        if norm not in seen:
            words.append(norm)
            seen.add(norm)
        if not is_cyrillic(part):
            cyr = latin_to_cyrillic(part).upper()
            if cyr != norm and cyr not in seen:
                words.append(cyr)
                seen.add(cyr)
        if is_cyrillic(part):
            lat = cyrillic_to_latin(part).upper()
            if lat != norm and lat not in seen:
                words.append(lat)
                seen.add(lat)
    return words


def extract_ocr_words(ocr_text: str) -> set:
    if not ocr_text:
        return set()
    words = re.findall(r'[A-Za-zА-Яа-яЁё0-9]+', ocr_text)
    result = set()
    
    # Словарь известных исключений, чтобы OCR слова сразу маппились в правильную кириллицу
    KNOWN_ALIASES = {
        "RIESLING": ["РИСЛИНГ", "RISLING"],
        "CHARDONNAY": ["ШАРДОНЕ", "SHARDONE"],
        "SAUVIGNON": ["СОВИНЬОН", "SOVINYON"],
        "SYRAH": ["СИРА", "SIRA"],
        "SHIRAZ": ["ШИРАЗ", "SHIRAZ"],
        "CABERNET": ["КАБЕРНЕ", "KABERNE"],
        "MERLOT": ["МЕРЛО", "MERLO"],
        "PINOT": ["ПИНО", "PINO"],
        "NOIR": ["НУАР", "NUAR"],
        "GRIGIO": ["ГРИДЖИО", "GRIDZHIO"],
        "BLANC": ["БЛАН", "BLAN"],
        "RESERVE": ["РЕЗЕРВ", "REZERVA", "РЕЗЕРВА"],
        "RESERVA": ["РЕЗЕРВ", "REZERVA", "РЕЗЕРВА"],
        "ROSE": ["РОЗОВОЕ", "ROZE"],
    }
    
    for w in words:
        norm = normalize_word(w)
        if len(norm) >= 2:
            result.add(norm)
            if is_cyrillic(w):
                result.add(cyrillic_to_latin(w).upper())
            elif not is_cyrillic(w):
                result.add(latin_to_cyrillic(w).upper())
                
            # Добавляем алиасы, если слово известно
            if norm in KNOWN_ALIASES:
                for alias in KNOWN_ALIASES[norm]:
                    result.add(alias)
    return result
    return result
def get_word_weight(word: str, brand_words: set = None) -> float:
    w = word.upper()
    if brand_words and w in brand_words:
        return 3.0
    if w in {"РЕЗЕРВ", "RESERVE", "RESERVA", "РЕЗЕРВА"}:
        return 3.0
    if w in {"КРАСНОЕ", "RED", "KRASNOE", "РОЗОВОЕ", "ROSE", "БЕЛОЕ", "BELOE", "WHITE"}:
        return 2.0
    
    # Сорта винограда
    grapes = {
        "СОВИНЬОН", "SAUVIGNON", "БЛАН", "БЛАНК", "BLANC", 
        "КОКУР", "KOKUR", "МЕРЛО", "MERLOT", "КАБЕРНЕ", "CABERNET", 
        "ПИНО", "PINOT", "НУАР", "NOIR", "ГРИДЖИО", "GRIGIO",
        "ШАРДОНЕ", "CHARDONNAY", "РИСЛИНГ", "RIESLING", "СИРА", "SYRAH", 
        "ШИРАЗ", "SHIRAZ", "КАРМЕНЕР", "CARMENERE", "МАЛЬБЕК", "MALBEC", 
        "САПЕРАВИ", "SAPERAVI", "ЗИНФАНДЕЛЬ", "ZINFANDEL", 
        "ГРЕНАШ", "GRENACHE", "МУСКАТ", "MUSCAT", "АЛИГОТЕ", "ALIGOTE",
        "СЕНСО", "CINSAULT", "ТЕМПРАНИЛЬО", "TEMPRANILLO"
    }
    if w in grapes:
        return 1.5
        
    return 1.0


def compute_divisor(matched_weight: float, total_weight: float) -> int:
    if total_weight <= 0:
        return 4
    ratio = matched_weight / total_weight
    if ratio >= 0.9:
        return 1
    elif ratio >= 0.5:
        return 2
    elif ratio >= 0.33:
        return 3
    else:
        return 4


class VinaStudioMatcher:
    def __init__(self, catalog):
        self.catalog = catalog
        self.slug_to_name = {}
        for wine in catalog.get_all_wines():
            slug = wine.get("slug", "")
            name = wine.get("name", "") or wine.get("title", "")
            if slug and name:
                self.slug_to_name[slug] = name
        print(f"[VinaStudioMatcher] Загружено {len(self.slug_to_name)} slug → name")
    
    def compute_ocr_bonus(self, slug: str, ocr_words: set) -> Tuple[int, int, int, List[str]]:
        slug_words = extract_slug_words(slug)
        
        brand_words = set()
        wine_info = self.catalog.get_wine(slug)
        if wine_info and wine_info.get("winery"):
            brand_words.update(extract_ocr_words(wine_info["winery"]))
            
        total_words = len(slug_words)
        total_weight = sum(get_word_weight(sw, brand_words) for sw in slug_words)
        
        matched = []
        matched_weight = 0.0
        
        for sw in slug_words:
            weight = get_word_weight(sw, brand_words)
            if sw in ocr_words:
                matched.append(sw)
                matched_weight += weight
        
        match_count = len(matched)
        divisor = compute_divisor(matched_weight, total_weight)
        return divisor, match_count, total_words, matched
    
    def cascade_decision(self, ocr_text: str, siglip_results: List[Dict], min_tags_threshold: int = 3) -> Dict:
        """
        Каскад v4: проверяем **топ-5** из SigLIP.
        """
        ocr_words = extract_ocr_words(ocr_text)
        # ← Топ-5 вместо топ-3
        top_candidates = siglip_results[:5] if siglip_results else []
        
        scored_candidates = []
        for candidate in top_candidates:
            slug = candidate["slug"]
            raw_score = float(candidate.get("score", 0.0))
            emb_confidence = max(0.0, min(100.0, (raw_score + 1.0) / 2.0 * 100.0))
            
            divisor, match_count, total_words, matched_words = self.compute_ocr_bonus(slug, ocr_words)
            
            # Штраф, если ни одно слово из названия не найдено (и OCR вообще что-то нашел)
            name_penalty = 0.0
            if ocr_words:
                wine_info = self.catalog.get_wine(slug)
                if wine_info and wine_info.get("name"):
                    name_words = extract_ocr_words(wine_info["name"])
                    if name_words and not any(nw in ocr_words for nw in name_words):
                        name_penalty = 10.0
                        
            ocr_bonus = (100.0 - emb_confidence) / divisor
            final_confidence = emb_confidence + ocr_bonus - name_penalty
            final_confidence = min(100.0, max(0.0, final_confidence))
            
            scored_candidates.append({
                "slug": slug,
                "name": self.slug_to_name.get(slug, ""),
                "raw_score": raw_score,
                "confidence_embedding": round(emb_confidence, 2),
                "ocr_bonus": round(ocr_bonus, 2),
                "divisor": divisor,
                "final_confidence": round(final_confidence, 2),
                "match_count": match_count,
                "total_words": total_words,
                "matched_words": matched_words,
            })
        
        scored_candidates.sort(key=lambda x: -x["final_confidence"])
        
        if not scored_candidates:
            return {"slug": None, "confidence_embedding": 0.0, "ocr_bonus": 0.0,
                    "final_confidence": 0.0, "decision_source": "empty", "candidates": []}
        
        best = scored_candidates[0]
        
        if best["divisor"] == 1:
            decision_source = "ocr_confirmed_all_words"
        elif best["divisor"] == 2:
            decision_source = "ocr_confirmed_half"
        elif best["divisor"] == 3:
            decision_source = "ocr_confirmed_third"
        else:
            decision_source = "embedding_primary"
        
        return {
            "slug": best["slug"],
            "name": best["name"],
            "confidence_embedding": best["confidence_embedding"],
            "ocr_bonus": best["ocr_bonus"],
            "divisor": best["divisor"],
            "final_confidence": best["final_confidence"],
            "decision_source": decision_source,
            "match_count": best["match_count"],
            "total_words": best["total_words"],
            "matched_words": best["matched_words"],
            "candidates": scored_candidates,
        }
