"""
Гибридный ранжировщик v2: SigLIP2 + DINOv2-LoRA -> топ-2 (N1, N2) -> бонусы OCR.

Формула (по ТЗ Алексея):
    N   = уверенность эмбеддинга кандидата, % (0..100)
    IB  = 100 - N                      (идеальный бонус: «добивает» до 100%)
    Бонус = A + C + D + F, где
        A = IB * 0.50 * a   — наименование вина / винзавода
        C = IB * 0.25 * c   — сорт винограда («рислинг не рислинг»)
        D = IB * 0.15 * d   — цвет
        F = IB * 0.10 * f   — сухость / сладость
    a, c, d, f ∈ [0..1] — доля совпадения слов OCR со slug + «Наименованием» (+ полями базы).
    IF  = N + Бонус. Побеждает кандидат с максимальным IF.
"""
import difflib
import re
from dataclasses import dataclass, field

from pipeline.vina_studio_matcher import (
    cyrillic_to_latin, latin_to_cyrillic, is_cyrillic,
)
from pipeline.wine_thesaurus import (
    GRAPE_ONTOLOGY,
    COLOR_ONTOLOGY,
    SWEETNESS_ONTOLOGY,
    SPECIAL_WINE_TERMS,
    SPECIAL_TERM_LOOKUP,
    BRAND_TERROIR_SYNONYMS,
    BRAND_SYN_LOOKUP,
    ALL_GRAPE_WORDS,
    extract_grape_concepts,
    normalize_ocr_text,
    match_term_in_ocr,
)

W_A, W_C, W_D, W_F = 0.50, 0.25, 0.15, 0.10

STOP = {
    "ВИНО", "WINE", "VINO", "VIN", "ЗАЩИЩЕННОГО", "ГЕОГРАФИЧЕСКОГО", "УКАЗАНИЯ", "НАИМЕНОВАНИЯ",
    "МЕСТА", "ПРОИСХОЖДЕНИЯ", "ВИНОДЕЛЬНЯ", "VINODELNYA", "WINERY", "ESTATE", "THE", "AND", "DE", "DI", "DEL",
    "LA", "LE", "ИЗ", "НА", "ОТ", "СОРТОВОЕ", "ТИХОЕ", "ИГРИСТОЕ", "COLLECTION", "КОЛЛЕКЦИЯ",
    "СОРТА", "СОРТОВ", "СОРТОВОЕ", "SORTA", "SORTOV", "ВИНОГРАД", "ВИНОГРАДА", "VINOGRAD", "VINOGRADA",
    "ПОРТВЕЙН", "PORT", "PORTO", "КАГОР", "KAGOR", "МАДЕРА", "MADEIRA", "ХЕРЕС", "SHERRY", "JEREZ",
    "ВЕРМУТ", "VERMOUTH", "ЛИКЕРНОЕ", "КРЕПЛЕНОЕ",
    "ИМЕНИЕ", "IMENIE", "УСАДЬБА", "USADBA", "ПОМЕСТЬЕ", "POMESTE", "POMESTYE",
    "СЕМЕЙНАЯ", "SEMEYNAYA", "SEMEJNAYA", "FAMILY",
    "АВТОРСКАЯ", "AVTORSKAYA", "АВТОРСКОЕ", "AVTORSKOE",
    "ФЕРМЕРСКАЯ", "FERMERSKAYA", "ФЕРМЕРСКОЕ", "FERMERSKOE",
    "ВИНОГРАДНИКИ", "VINEYARDS", "VINEYARD",
    "ДЕРЕВНЯ", "DEREVNYA", "ВИННАЯ", "VINNAYA",
    "ХОЗЯЙСТВО", "HOZYAYSTVO", "ДОМ", "DOM", "HOUSE", "ЗАВОД", "ZAVOD",
}


@dataclass
class BonusResult:
    a: float = 0.0
    c: float = 0.0
    d: float = 0.0
    f: float = 0.0
    matched: dict = field(default_factory=dict)


def compute_match_fractions(ocr_text: str, wine: dict) -> BonusResult:
    """
    Вычисление долей совпадения (a, c, d, f) через полномасштабный мультиязычный тезаурус:
    - C (0.25): Сорт винограда через онтологию (Каберне <-> Cabernet, Мерло <-> Merlot и т.д.)
    - D (0.15): Цвет через мультиязычную онтологию (Красное/Red/Rouge, Белое/White/Blanc, Розовое/Rose/Rosado)
    - F (0.10): Сахар/сухость через онтологию (Сухое/Dry/Sec, Полусладкое/Semi-sweet и т.д.)
    - A (0.50): Ступенчатое правило Алексея:
        * 0 совпавших слов бренда -> 0.0
        * 1 совпавшее слово бренда -> 0.5 (половина потолка)
        * 2 и более слов бренда    -> 1.0 (полный потолок)
    """
    res = BonusResult()
    if not ocr_text or not wine:
        return res

    ocr_words, ocr_joined, ocr_compact = normalize_ocr_text(ocr_text)
    _match = lambda t: match_term_in_ocr(t, ocr_words, ocr_joined, ocr_compact)

    # --- КАТЕГОРИЯ C: СОРТ ВИНОГРАДА (Через Мультиязычную Онтологию) ---
    wine_grapes = extract_grape_concepts(wine.get("grape", ""))
    if not wine_grapes:
        wine_grapes = extract_grape_concepts(wine.get("name", ""))
    if not wine_grapes:
        # Резервный поиск сорта в слаге вина
        slug_plain = wine.get("slug", "").replace("-", " ")
        wine_grapes = extract_grape_concepts(slug_plain)

    # Детекция сортов в распознанном тексте этикетки OCR (для выявления противоречий)
    ocr_grapes = extract_grape_concepts(ocr_text)
    if not ocr_grapes:
        for concept, variants in GRAPE_ONTOLOGY.items():
            for variant in variants:
                if _match(variant):
                    ocr_grapes.add(concept)
                    break

    hits_c = []
    if ocr_grapes:
        hits_c = [c for c in wine_grapes if c in ocr_grapes]
    else:
        for concept in wine_grapes:
            for variant in GRAPE_ONTOLOGY.get(concept, []):
                if _match(variant):
                    hits_c.append(concept)
                    break

    # Исключение для уникальных монопольных линеек каталога (Крепость Саркел):
    # В каталоге организатора представлена ровно одна карточка этой премиальной линейки
    is_krepost_sarkel = "krepost-sarkel" in wine.get("slug", "") and _match("КРЕПОСТЬ") and _match("САРКЕЛ")

    if hits_c:
        res.c = round(len(hits_c) / len(wine_grapes), 3) if wine_grapes else 0.0
    elif wine_grapes and ocr_grapes:
        if is_krepost_sarkel:
            res.c = 0.0
        else:
            # Штраф ТЗ Алексея: -0.25 * идеальный бонус при несовпадении/противоречии сорта
            res.c = -1.0
    else:
        res.c = 0.0

    res.matched["C"] = hits_c

    # --- КАТЕГОРИЯ D: ЦВЕТ (Через Мультиязычную Онтологию с проверкой противоречий) ---
    cat_val = (wine.get("category", "") or "").lower()
    detected_colors = set()
    for col_key, words in COLOR_ONTOLOGY.items():
        if any(_match(w) for w in words):
            detected_colors.add(col_key[:4])

    wine_col_prefix = next((col_key[:4] for col_key in COLOR_ONTOLOGY if cat_val.startswith(col_key[:4])), None)
    if wine_col_prefix and wine_col_prefix in detected_colors:
        res.d = 1.0
        res.matched["D"] = [w for w in COLOR_ONTOLOGY.get(cat_val[:4], []) if _match(w)]
    elif wine_col_prefix and detected_colors and wine_col_prefix not in detected_colors:
        # Противоречие цвета: на этикетке явно указан один цвет (напр., Rose), а вино в базе другого цвета
        res.d = -1.0
    else:
        res.d = 0.0

    # --- КАТЕГОРИЯ F: СУХОСТЬ / СЛАДОСТЬ (Через Мультиязычную Онтологию) ---
    sw_val = (wine.get("sweetness", "") or "").lower().strip()
    if not sw_val:
        slug_plain = wine.get("slug", "").replace("-", " ").lower()
        for sw_key, words in SWEETNESS_ONTOLOGY.items():
            if any(w.lower() in slug_plain for w in words):
                sw_val = sw_key
                break

    detected_sweet = set()
    for sw_key, words in SWEETNESS_ONTOLOGY.items():
        if any(_match(w) for w in words):
            detected_sweet.add(sw_key)
    if sw_val in detected_sweet:
        res.f = 1.0
        res.matched["F"] = [sw_val]
    elif sw_val and detected_sweet and sw_val not in detected_sweet:
        # Противоречие сахара/сухости: на этикетке указан один тип сладости, а кандидат другого типа
        res.f = -1.0
    else:
        res.f = 0.0

    # --- КАТЕГОРИЯ A: НАИМЕНОВАНИЕ / БРЕНД (Ступенчатое правило Алексея) ---
    color_all = set().union(*COLOR_ONTOLOGY.values())
    sweet_all = set().union(*SWEETNESS_ONTOLOGY.values())

    def brand_tokens(text):
        out = []
        for t in re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", text or ""):
            t_u = t.upper()
            if len(t_u) < 3 or t_u.isdigit() or t_u in STOP or t_u in color_all or t_u in sweet_all:
                if t_u not in SPECIAL_TERM_LOOKUP:
                    continue
            if t_u in ALL_GRAPE_WORDS:
                continue
            out.append(t_u)
        return out

    toks_name = brand_tokens(wine.get("name", ""))
    toks_winery = brand_tokens(wine.get("winery", ""))
    slug_words = [t for t in re.split(r"[-_]", wine.get("slug", "")) if t and not t.isdigit()]
    toks_slug = brand_tokens(" ".join(slug_words))

    # Каноническая дедупликация (чтобы русское и латинское слово одного бренда/термина не задваивались)
    canon_map = {}
    for t in (toks_name + toks_winery + toks_slug):
        if t in SPECIAL_TERM_LOOKUP:
            c = "SPECIAL_" + SPECIAL_TERM_LOOKUP[t]
        elif t in BRAND_SYN_LOOKUP:
            c = "BRAND_" + BRAND_SYN_LOOKUP[t]
        else:
            c = (cyrillic_to_latin(t) if is_cyrillic(t) else t).upper()
        if c not in canon_map:
            canon_map[c] = t

    # Основные смысловые концепты вина (название + винодельня, без шума длинных слагов)
    canon_core = {}
    for t in (toks_name + toks_winery):
        if t in SPECIAL_TERM_LOOKUP:
            c = "SPECIAL_" + SPECIAL_TERM_LOOKUP[t]
        elif t in BRAND_SYN_LOOKUP:
            c = "BRAND_" + BRAND_SYN_LOOKUP[t]
        else:
            c = (cyrillic_to_latin(t) if is_cyrillic(t) else t).upper()
        if c not in canon_core:
            canon_core[c] = t

    # Каноническое сопоставление концептов (каждый концепт оценивается ровно 1 раз, исключая задвоения)
    matched_concepts = set()
    matched_display = []
    for c, orig in canon_core.items():
        if c.startswith("SPECIAL_"):
            concept = c.replace("SPECIAL_", "")
            if any(_match(v) for v in SPECIAL_WINE_TERMS.get(concept, [])):
                matched_concepts.add(c)
                matched_display.append(orig)
        elif c.startswith("BRAND_"):
            concept = c.replace("BRAND_", "")
            found_syn = [v for v in BRAND_TERROIR_SYNONYMS.get(concept, []) if _match(v)]
            if found_syn:
                matched_concepts.add(c)
                matched_display.extend(found_syn)
        else:
            lat = (cyrillic_to_latin(orig) if is_cyrillic(orig) else orig).upper()
            cyr = (latin_to_cyrillic(orig) if not is_cyrillic(orig) else orig).upper()
            if _match(orig) or _match(lat) or _match(cyr):
                matched_concepts.add(c)
                matched_display.append(orig)

    # Проверка многословных линеек/терминов (например, 'BLANC DE BLANCS')
    full_wine_str = f"{wine.get('name', '')} {wine.get('slug', '').replace('-', ' ')}".upper()
    for concept, variants in SPECIAL_WINE_TERMS.items():
        c_key = "SPECIAL_" + concept
        if c_key not in canon_core and any(v in full_wine_str for v in variants):
            if any(_match(v) for v in variants):
                matched_concepts.add(c_key)
                matched_display.append(concept)

    n_m = len(matched_concepts)
    total_tokens = len(canon_core) if canon_core else max(1, len(canon_map))

    # Ступенчатое правило Алексея с учетом покрытия уникальных концептов наименования:
    coverage = n_m / max(1, total_tokens)
    if n_m == 0:
        res.a = 0.0
    elif total_tokens <= 1 and n_m >= 1:
        res.a = 1.0
    elif n_m == 1:
        res.a = 0.5
    else:
        # n_m >= 2: прогрессивная шкала от 0.55 до 1.0 при полном покрытии всех слов названия
        res.a = min(1.0, round(0.55 + 0.45 * (min(1.0, coverage) ** 2.0), 3))

    # Взаимоисключающие стили игристых вин (Blanc de Blancs vs Blanc de Noirs):
    # Если на этикетке четко указан один из стилей, кандидат с противоположным стилем не может иметь полный потолок
    has_b_blancs = any(_match(v) for v in SPECIAL_WINE_TERMS.get("BLANC_DE_BLANCS", []))
    has_b_noirs = any(_match(v) for v in SPECIAL_WINE_TERMS.get("BLANC_DE_NOIRS", []))
    wine_has_noirs = any(v in full_wine_str for v in SPECIAL_WINE_TERMS.get("BLANC_DE_NOIRS", []))
    wine_has_blancs = any(v in full_wine_str for v in SPECIAL_WINE_TERMS.get("BLANC_DE_BLANCS", []))

    if has_b_blancs and wine_has_noirs:
        res.a = min(res.a, 0.5)
    elif has_b_noirs and wine_has_blancs:
        res.a = min(res.a, 0.5)

    # Взаимоисключающие линейки вкусов (Berry Explosion vs Fruit Explosion):
    has_berry = any(_match(v) for v in SPECIAL_WINE_TERMS.get("BERRY_EXPLOSION", []))
    has_fruit = any(_match(v) for v in SPECIAL_WINE_TERMS.get("FRUIT_EXPLOSION", []))
    wine_has_fruit = any(v in full_wine_str for v in SPECIAL_WINE_TERMS.get("FRUIT_EXPLOSION", []))
    wine_has_berry = any(v in full_wine_str for v in SPECIAL_WINE_TERMS.get("BERRY_EXPLOSION", []))

    if has_berry and wine_has_fruit:
        res.a = min(res.a, 0.25)
    elif has_fruit and wine_has_berry:
        res.a = min(res.a, 0.25)

    # Проверка сорта в названии вина:
    # Если название кандидата прямо содержит сорт (напр., "Шардоне Резерв"), но этого сорта нет на этикетке:
    if not is_krepost_sarkel:
        wine_name_grapes = extract_grape_concepts(wine.get("name", ""))
        if wine_name_grapes and not any(g in ocr_grapes for g in wine_name_grapes):
            res.a = min(res.a, 0.5)

    # Защита от неподтвержденного Резерва (Unverified Reserve Guard):
    # Если кандидат заявляет Резерв/Семейный, а на этикетке нет ни одного признака Резерва — штраф (a = min(a, 0.25))
    # И наоборот: если этикетка содержит Резерв, а кандидат — базовое вино без Резерва — штраф (a = min(a, 0.25))
    is_reserve_candidate = any(v in full_wine_str for v in SPECIAL_WINE_TERMS.get("RESERVE", []))
    ocr_has_reserve = any(_match(v) for v in SPECIAL_WINE_TERMS.get("RESERVE", []))

    # Защита линеек Мускатель vs Мускат vs Портвейн:
    has_muskatel = any(_match(v) for v in SPECIAL_WINE_TERMS.get("MUSKATEL", []))
    wine_has_muskatel = any(v in full_wine_str for v in SPECIAL_WINE_TERMS.get("MUSKATEL", []))
    if has_muskatel:
        if wine_has_muskatel:
            res.a = 1.0
            matched_display.append("МУСКАТЕЛЬ")
        else:
            res.a = min(res.a, 0.20)
    elif wine_has_muskatel and not has_muskatel:
        res.a = min(res.a, 0.20)

    res.matched["A"] = list(dict.fromkeys(matched_display))
    return res


def apply_bonus(n: float, frac: BonusResult) -> dict:
    ib = max(0.0, 100.0 - n)
    penalty_base = max(ib, 40.0)
    
    A = ib * W_A * frac.a
    C = (ib if frac.c >= 0 else penalty_base) * W_C * frac.c
    D = (ib if frac.d >= 0 else penalty_base) * W_D * frac.d
    F = (ib * W_F * frac.f) if frac.f >= 0 else -15.0

    # Если этикетка прямо противоречит сахару кандидата (напр., на этикетке полусладкое, а в базе сухое),
    # такое вино не может быть верным, сортовой бонус обнуляется, а бонус за бренд урезается
    if frac.f < 0:
        C = min(0.0, C)
        A = min(A, ib * 0.15)
    
    if_val = max(0.0, min(100.0, n + A + C + D + F))
    return {"N": round(n, 2), "IB": round(ib, 2), "A": round(A, 2), "C": round(C, 2),
            "D": round(D, 2), "F": round(F, 2), "IF": round(if_val, 2),
            "a": frac.a, "c": frac.c, "d": frac.d, "f": frac.f, "matched": frac.matched}


def calibrate_zscore_sigmoid(score_dict: dict, temp: float = 2.0) -> dict:
    """Приведение сырых косинусных расстояний к калиброванной вероятностной шкале [0..1] через z-score."""
    import math
    import numpy as np
    vals = np.array(list(score_dict.values()))
    mu, sigma = float(np.mean(vals)), max(float(np.std(vals)), 1e-6)
    return {k: 1.0 / (1.0 + math.exp(-((v - mu) / sigma) / temp)) for k, v in score_dict.items()}


class HybridRanker:
    """
    SigLIP2 + DINOv2-LoRA:
    1. Получение Top-K кандидатов от SigLIP и Top-K от DINO (объединенный пул до 2*K вин).
    2. Приведение оценок к единой шкале (Z-score + Sigmoid или Affine).
    3. Вычисление уверенности N = 100 * (w_s * s_sig + w_d * s_dino).
    4. Применение бонусов OCR (A, C, D, F) и ранжирование по IF.
    """

    def __init__(self, siglip_engine, dino_engine, catalog, 
                 w_siglip: float = 0.7, w_dino: float = 0.3,
                 pool_k_sig: int = 15, pool_k_dino: int = 15,
                 calibrate: bool = True):
        self.sig, self.dino, self.catalog = siglip_engine, dino_engine, catalog
        self.w_s, self.w_d = w_siglip, w_dino
        self.pool_k_sig = pool_k_sig
        self.pool_k_dino = pool_k_dino
        self.calibrate = calibrate
        
        # Индекс вин по винодельням для мгновенного расширения кластера сестринских вин
        self.winery_to_slugs = {}
        for w in catalog.get_all_wines():
            win = w.get("winery", "").strip().lower()
            if win:
                self.winery_to_slugs.setdefault(win, []).append(w["slug"])

    @staticmethod
    def _all_scores(index, slugs, emb):
        scores, idx = index.search(emb, index.ntotal)
        out = {}
        for s, i in zip(scores[0], idx[0]):
            if i >= 0:
                sl = slugs[i]
                if sl not in out:
                    out[sl] = float(s)
        return out

    def embedding_scores(self, bgr):
        import cv2
        from PIL import Image
        pil = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        s_sig = self._all_scores(self.sig.index, self.sig.slugs, self.sig.get_embedding(pil))
        s_dino = self._all_scores(self.dino.index, self.dino.slugs,
                                  self.dino.embed_bgr([self.dino.crop_label(bgr)]))
        return s_sig, s_dino

    def rank(self, bgr, ocr_text: str, top_n: int = 2, s_sig=None, s_dino=None):
        if s_sig is None or s_dino is None:
            s_sig, s_dino = self.embedding_scores(bgr)

        # Калибровка шкал при необходимости
        if self.calibrate:
            s_sig_norm = calibrate_zscore_sigmoid(s_sig, temp=2.0)
            s_dino_norm = calibrate_zscore_sigmoid(s_dino, temp=2.0)
        else:
            s_sig_norm, s_dino_norm = s_sig, s_dino

        # 1. Формируем первичный пул кандидатов: Top-K от SigLIP + Top-K от DINO
        sig_top = [s for s, _ in sorted(s_sig_norm.items(), key=lambda x: -x[1])[:self.pool_k_sig]]
        dino_top = [s for s, _ in sorted(s_dino_norm.items(), key=lambda x: -x[1])[:self.pool_k_dino]]
        candidate_pool = list(dict.fromkeys(sig_top + dino_top))

        # 2. Расширение пула через винодельни (Winery Sister Cluster Expansion):
        # Если в Top-4 визуала определена винодельня, добавляем сестринские вина этой винодельни
        winery_slugs = []
        for s in candidate_pool[:4]:
            w = self.catalog.get_wine(s)
            if w and w.get("winery"):
                win_k = w["winery"].strip().lower()
                if win_k in self.winery_to_slugs:
                    winery_slugs.extend(self.winery_to_slugs[win_k][:15])
        candidate_pool = list(dict.fromkeys(candidate_pool + winery_slugs))

        # 3. Текстовое расширение из OCR:
        if ocr_text:
            ocr_w = set(re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", ocr_text.upper()))
            text_slugs = []
            for w in self.catalog.get_all_wines():
                name_w = set(re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", (w.get("name", "") + " " + w.get("slug", "")).upper()))
                common = (name_w & ocr_w) - STOP
                if len(common) >= 2:
                    text_slugs.append(w["slug"])
            candidate_pool = list(dict.fromkeys(candidate_pool + text_slugs))

        # Специальный визуальный детектор шильдика для вин линейки «Фантом» (Ведерниковъ)
        fantom_cuvee = None
        if any("fantom" in s for s in candidate_pool):
            # Гарантируем наличие всех купажей Фантом в пуле кандидатов
            for w in self.catalog.get_all_wines():
                if "fantom" in w.get("slug", "") and w["slug"] not in candidate_pool:
                    candidate_pool.append(w["slug"])
            try:
                lbl_bgr = self.dino.crop_label(bgr)
                lh, lw = lbl_bgr.shape[:2]
                badge = lbl_bgr[int(lh * 0.75):int(lh * 0.95), :int(lw * 0.22)]
                import cv2
                import numpy as np
                hsv = cv2.cvtColor(badge, cv2.COLOR_BGR2HSV)
                mask = (hsv[:, :, 1] > 35) & (hsv[:, :, 2] > 40)
                if np.any(mask):
                    colored = badge[mask]
                    b_m, g_m, r_m = colored.mean(axis=0)
                    v_m = hsv[mask][:, 2].mean()
                    if v_m < 85 and abs(r_m - b_m) < 15:
                        fantom_cuvee = "5050"
                    elif r_m > b_m + 15:
                        fantom_cuvee = "3070"
                    elif b_m > r_m + 10:
                        fantom_cuvee = "7030"
                    print(f"[HybridRanker] Fantom badge detected: {fantom_cuvee} (R={r_m:.1f}, B={b_m:.1f}, V={v_m:.1f})")
            except Exception as e_f:
                print(f"[HybridRanker] Fantom badge detection warning: {e_f}")

        out = []
        for slug in candidate_pool:
            sn = s_sig_norm.get(slug, 0.5)
            dn = s_dino_norm.get(slug, 0.5)
            n = 100.0 * (self.w_s * sn + self.w_d * dn)
            wine = self.catalog.get_wine(slug)
            frac = compute_match_fractions(ocr_text, wine)
            
            # Селектор шильдика для линейки Фантом:
            if fantom_cuvee and "fantom" in slug:
                if fantom_cuvee in slug:
                    frac.a = 1.0
                else:
                    frac.a = min(frac.a, 0.1)

            b = apply_bonus(n, frac)
            b.update({
                "slug": slug,
                "name": wine.get("name", "") if wine else "",
                "siglip_raw": round(s_sig.get(slug, 0.0), 4),
                "dino_raw": round(s_dino.get(slug, 0.0), 4),
                "siglip_norm": round(sn, 4),
                "dino_norm": round(dn, 4)
            })
            out.append(b)
        # Сортируем: в первую очередь по итоговому баллу IF, а при равенстве (100.0) — по уверенности эмбеддинга N
        out.sort(key=lambda r: (round(r["IF"], 2), round(r["N"], 2)), reverse=True)
        return out[:top_n]

