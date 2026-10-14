
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


def extract_slug_words(slug: str) -> List[tuple]:
    parts = slug.replace('_', '-').split('-')
    words = []
    seen_groups = set()
    for part in parts:
        if not part or len(part) < 2:
            continue
        if part.isdigit() and len(part) == 4 and (part.startswith("20") or part.startswith("19")):
            continue
            
        norm = part.upper()
        group = [norm]
        if not is_cyrillic(part):
            cyr = latin_to_cyrillic(part).upper()
            if cyr != norm:
                group.append(cyr)
        if is_cyrillic(part):
            lat = cyrillic_to_latin(part).upper()
            if lat != norm:
                group.append(lat)
        
        group_tuple = tuple(set(group))
        if group_tuple not in seen_groups:
            seen_groups.add(group_tuple)
            words.append(group_tuple)
            
    return words


def extract_ocr_words(ocr_text: str) -> set:
    if not ocr_text:
        return set()
    words = re.findall(r'[A-Za-zА-Яа-яЁё0-9]+', ocr_text)
    result = set()
    
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
        if w.isdigit() and len(w) == 4 and (w.startswith("20") or w.startswith("19")):
            continue
        norm = normalize_word(w)
        if len(norm) >= 2:
            result.add(norm)
            if is_cyrillic(w):
                result.add(cyrillic_to_latin(w).upper())
            elif not is_cyrillic(w):
                result.add(latin_to_cyrillic(w).upper())
                
            if norm in KNOWN_ALIASES:
                for alias in KNOWN_ALIASES[norm]:
                    result.add(alias)
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


# --- Простой режим (simple_decision): SigLIP + различающиеся слова среди соседей ---
SIMPLE_MARGIN = 2.0   # пунктов эмбеддинга (score*100): кто считается «соседом» лидера
SIMPLE_HIT = 1.0      # + за каждое различающееся слово slug, найденное в OCR
SIMPLE_MISS = 0.5     # доля штрафа за ненайденное (штраф = SIMPLE_HIT * SIMPLE_MISS)


def _slug_tokens(slug: str) -> List[str]:
    # В отличие от extract_slug_words, цифры сохраняем (год, 7030/5050)
    return [t for t in re.split(r'[-_]', slug) if len(t) >= 2]


def _token_variants(tok: str) -> set:
    t = tok.upper()
    return {t, (cyrillic_to_latin(t) if is_cyrillic(t) else latin_to_cyrillic(t)).upper()}


def _token_in_ocr(tok: str, ocr_words: set, ocr_no_spaces: str) -> bool:
    import difflib
    for v in _token_variants(tok):
        if v in ocr_words:
            return True
        if len(v) >= 4 and v in ocr_no_spaces:
            return True
        if len(v) >= 5:
            for o in ocr_words:
                if len(o) >= 4 and difflib.SequenceMatcher(None, v, o).ratio() >= 0.85:
                    return True
    return False


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
    
    def compute_ocr_bonus(self, slug: str, ocr_words: set, ocr_text: str = "") -> Tuple[int, int, int, List[str]]:
        import difflib
        slug_word_groups = extract_slug_words(slug)
        
        brand_words = set()
        wine_info = self.catalog.get_wine(slug)
        if wine_info and wine_info.get("winery"):
            brand_words.update(extract_ocr_words(wine_info["winery"]))
            
        total_words = len(slug_word_groups)
        total_weight = 0.0
        
        for group in slug_word_groups:
            # Вес берется по первому варианту (оригиналу)
            total_weight += get_word_weight(group[0], brand_words)
        
        # Склеенный текст OCR без пробелов для поиска разбитых слов (напр. A B R A U)
        ocr_no_spaces = "".join([w for w in ocr_text.upper() if w.isalnum()])
        
        matched = []
        matched_weight = 0.0
        
        for group in slug_word_groups:
            group_matched = False
            matched_variant = ""
            
            for sw in group:
                is_match = False
                
                # Точное совпадение
                if sw in ocr_words:
                    is_match = True
                
                # Поиск слова в склеенном тексте (решает разрывы букв A B R A U -> ABRAU)
                if not is_match and len(sw) >= 5 and sw in ocr_no_spaces:
                    is_match = True
                
                # Fuzzy match (расстояние Левенштейна / сходство)
                if not is_match and len(sw) >= 4:
                    for ocr_w in ocr_words:
                        if len(ocr_w) < 4:
                            continue
                        ratio = difflib.SequenceMatcher(None, sw, ocr_w).ratio()
                        # Если длина >= 8, прощаем больше опечаток (0.65+). 
                        # Если >= 6, (0.75+). Если короче, строже (0.8+)
                        if (len(sw) >= 8 and ratio >= 0.65) or \
                           (len(sw) >= 6 and len(sw) < 8 and ratio >= 0.75) or \
                           (len(sw) < 6 and ratio >= 0.8):
                            is_match = True
                            break
                            
                if is_match:
                    group_matched = True
                    matched_variant = sw
                    break # Слово совпало по одному из вариантов, дальше не ищем
                    
            if group_matched:
                matched.append(matched_variant)
                matched_weight += get_word_weight(group[0], brand_words)
        
        match_count = len(matched)
        divisor = compute_divisor(matched_weight, total_weight)
        return divisor, match_count, total_words, matched, matched_weight
    
    def cascade_decision(self, ocr_text: str, siglip_results: List[Dict], min_tags_threshold: int = 3) -> Dict:
        """
        Каскад v4: проверяем **топ-5** из SigLIP. 
        Оценка по эмбеддингам + человеческая эвристика (Цвет -> Резерв -> Сорт).
        """
        ocr_words = extract_ocr_words(ocr_text)
        top_candidates = siglip_results[:5] if siglip_results else []
        
        # Определяем цвета по OCR
        explicit_red = bool({"КРАСНОЕ", "RED", "КРАСНЫЙ", "КРАСНАЯ"} & ocr_words)
        explicit_white = bool({"БЕЛОЕ", "WHITE", "БЕЛЫЙ", "БЕЛАЯ"} & ocr_words)
        explicit_rose = bool({"РОЗОВОЕ", "ROSE", "РОЗОВЫЙ", "РОЗОВАЯ", "ROZE"} & ocr_words)
        
        grape_red = bool({"NOIR", "НУАР", "CABERNET", "КАБЕРНЕ", "MERLOT", "МЕРЛО", "SYRAH", "СИРА", "SHIRAZ", "ШИРАЗ", "SAPERAVI", "САПЕРАВИ"} & ocr_words)
        grape_white = bool({"БЛАН", "BLANC", "CHARDONNAY", "ШАРДОНЕ", "RIESLING", "РИСЛИНГ", "ALIGOTE", "АЛИГОТЕ", "РКАЦИТЕЛИ", "RKATSITELI"} & ocr_words)
        
        ocr_has_reserve = bool({"РЕЗЕРВ", "RESERVE", "RESERVA", "РЕЗЕРВА", "ВЫДЕРЖАННОЕ"} & ocr_words)
        
        scored_candidates = []
        for candidate in top_candidates:
            slug = candidate["slug"]
            raw_score = float(candidate.get("score", 0.0))
            emb_confidence = max(0.0, min(100.0, (raw_score + 1.0) / 2.0 * 100.0))
            
            divisor, match_count, total_words, matched_words, matched_weight = self.compute_ocr_bonus(slug, ocr_words, ocr_text)
            
            heuristics_score = 0.0
            wine_info = self.catalog.get_wine(slug) or {}
            
            # --- Улика 1: Цвет ---
            cat_red = False
            cat_white = False
            cat_rose = False
            
            category = wine_info.get("category", "").lower()
            slug_lower = slug.lower()
            
            if "красн" in category or "-krasnoe" in slug_lower or "krasnoe" in slug_lower or "-red" in slug_lower: 
                cat_red = True
            elif "бел" in category or "-beloe" in slug_lower or "beloe" in slug_lower or "-white" in slug_lower: 
                cat_white = True
            elif "роз" in category or "-rozovoe" in slug_lower or "rozovoe" in slug_lower or "-rose" in slug_lower or "roze" in slug_lower: 
                cat_rose = True
                
            # Бонусы за совпадение цвета
            if cat_red and (explicit_red or grape_red): heuristics_score += 15.0
            elif cat_white and (explicit_white or grape_white): heuristics_score += 15.0
            elif cat_rose and explicit_rose: heuristics_score += 15.0
            
            # Штрафы за противоречие цвета
            if cat_red and (explicit_white or explicit_rose or grape_white) and not (explicit_red or grape_red): 
                heuristics_score -= 30.0
            elif cat_white and explicit_red and not explicit_white: 
                heuristics_score -= 30.0
            elif cat_rose and (explicit_white or explicit_red) and not explicit_rose: 
                heuristics_score -= 30.0
                
            # --- Улика 2: Резерв ---
            slug_name_lower = slug_lower + " " + wine_info.get("name", "").lower()
            cat_is_reserve = any(w in slug_name_lower for w in ["reserve", "reserva", "rezerv", "резерв", "выдержан"])
            
            if ocr_has_reserve and cat_is_reserve:
                heuristics_score += 15.0
            elif ocr_has_reserve and not cat_is_reserve:
                heuristics_score -= 20.0
            # --- Улика 3: Сорт и базовый OCR ---
            # Старая логика: если есть совпадения, даем OCR бонус
            if match_count == 0:
                ocr_bonus = 0.0
            else:
                ocr_bonus = (100.0 - emb_confidence) / divisor
                # Штраф за короткие имена брендов в базе (например Golubitskoe),
                # чтобы они не перевешивали конкретные вина за счет 100% совпадения одного слова
                if total_words < 4:
                    ocr_bonus *= (total_words / 4.0)
                
                # Добавляем небольшой линейный бонус за каждый совпавший вес,
                # чтобы различать кандидатов, попавших в один divisor
                ocr_bonus += matched_weight * 1.5
                
            # Временно отключаем штраф за полное несовпадение названия (name_penalty)
            # из-за проблем с транслитерацией (например SAPERAVI в OCR и Саперави в базе)
            name_penalty = 0.0
            
            raw_final_confidence = emb_confidence + ocr_bonus - name_penalty + heuristics_score
            final_confidence = min(100.0, max(0.0, raw_final_confidence))
            
            scored_candidates.append({
                "slug": slug,
                "name": self.slug_to_name.get(slug, ""),
                "raw_score": raw_score,
                "confidence_embedding": round(emb_confidence, 2),
                "ocr_bonus": round(ocr_bonus, 2),
                "divisor": divisor,
                "final_confidence": round(final_confidence, 2),
                "raw_final_confidence": raw_final_confidence,
                "match_count": match_count,
                "total_words": total_words,
                "matched_words": matched_words,
            })
        
        scored_candidates.sort(key=lambda x: -x["raw_final_confidence"])
        
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

    def simple_decision(self, ocr_text: str, siglip_results: List[Dict]) -> Dict:
        """
        Простой режим (замена каскада v4, подобран на 92 размеченных фото, CV ~ +3 фото к SigLIP).
        1. Базовый балл = score SigLIP * 100.
        2. «Соседи» = кандидаты в пределах SIMPLE_MARGIN от лидера. Если соседей > 1,
           для каждого берутся слова slug, которых нет у ВСЕХ соседей (различающие),
           и сверяются с OCR (включая цифры): +SIMPLE_HIT за найденное, −SIMPLE_HIT*SIMPLE_MISS за нет.
        3. Победитель — максимум. Цвет, резерв, divisor и clamp не используются.
        Уверенность НЕ откалибрована: растёт с разрывом между 1-м и 2-м кандидатом.
        """
        cands = list(siglip_results or [])
        if not cands:
            return {"slug": None, "confidence_embedding": 0.0, "ocr_bonus": 0.0,
                    "final_confidence": 0.0, "decision_source": "empty", "candidates": []}

        ocr_words = {t.upper() for t in re.findall(r'[A-Za-zА-Яа-яЁё0-9]+', ocr_text or "")}
        ocr_words |= extract_ocr_words(ocr_text)
        ocr_ns = "".join(ch for ch in (ocr_text or "").upper() if ch.isalnum())

        embs = [float(c.get("score", 0.0)) * 100.0 for c in cands]
        top = max(embs)
        neigh = [i for i, e in enumerate(embs) if e >= top - SIMPLE_MARGIN]
        common = set()
        if len(neigh) > 1:
            common = set.intersection(*[{t.upper() for t in _slug_tokens(cands[i]["slug"])} for i in neigh])

        scored = []
        for i, c in enumerate(cands):
            slug = c["slug"]
            hits, miss = [], 0
            if len(neigh) > 1 and i in neigh:
                for t in _slug_tokens(slug):
                    if t.upper() in common:
                        continue
                    if _token_in_ocr(t, ocr_words, ocr_ns):
                        hits.append(t.upper())
                    else:
                        miss += 1
            bonus = SIMPLE_HIT * (len(hits) - SIMPLE_MISS * miss)
            scored.append({
                "slug": slug,
                "name": self.slug_to_name.get(slug, ""),
                "raw_score": float(c.get("score", 0.0)),
                "confidence_embedding": round(embs[i], 2),
                "ocr_bonus": round(bonus, 2),
                "divisor": 0,
                "raw_final_confidence": embs[i] + bonus,
                "match_count": len(hits),
                "total_words": len(hits) + miss,
                "matched_words": hits,
            })
        scored.sort(key=lambda x: -x["raw_final_confidence"])
        gap = scored[0]["raw_final_confidence"] - (scored[1]["raw_final_confidence"] if len(scored) > 1 else 0.0)
        conf = max(50.0, min(99.0, 50.0 + 10.0 * gap))
        for s in scored:
            s["final_confidence"] = round(conf if s is scored[0] else max(0.0, conf - 10.0 * gap - 1.0), 2)
        best = scored[0]
        return {
            "slug": best["slug"], "name": best["name"],
            "confidence_embedding": best["confidence_embedding"],
            "ocr_bonus": best["ocr_bonus"], "divisor": 0,
            "final_confidence": best["final_confidence"],
            "decision_source": "simple_neighbors_ocr" if len(neigh) > 1 else "simple_embedding",
            "match_count": best["match_count"], "total_words": best["total_words"],
            "matched_words": best["matched_words"], "candidates": scored,
        }
