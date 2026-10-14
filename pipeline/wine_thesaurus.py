"""
Модуль мультиязычного винного тезауруса (Wine Multilingual Thesaurus & Ontology).
Обеспечивает повсеместное сопоставление сортов винограда, цветов, сладости и терминов
на русском, английском, французском, итальянском, немецком и испанском языках,
а также сквозное устранение артефактов OCR (разреженный кернинг, пунктуация, транслитерация).
"""
import re
import difflib

# 1. ОНТОЛОГИЯ СОРТОВ ВИНОГРАДА (Канонический кластер синонимов)
GRAPE_ONTOLOGY = {
    "КАБЕРНЕ СОВИНЬОН": [
        "CABERNET SAUVIGNON", "КАБЕРНЕ СОВИНЬОН", "KABERNE SOVINON", "КАБЕРНЕ-СОВИНЬОН",
        "SAUVIGNON", "СОВИНЬОН", "SOVINON", "CABERNET", "КАБЕРНЕ", "KABERNE"
    ],
    "КАБЕРНЕ ФРАН": [
        "CABERNET FRANC", "КАБЕРНЕ ФРАН", "KABERNE FRAN", "КАБЕРНЕ-ФРАН",
        "FRANC", "ФРАН", "FRAN"
    ],
    "МЕРЛО": [
        "MERLOT", "MERLO", "МЕРЛО"
    ],
    "ШАРДОНЕ": [
        "CHARDONNAY", "CHARDONNA", "SHARDONE", "ШАРДОНЕ"
    ],
    "СОВИНЬОН БЛАН": [
        "SAUVIGNON BLANC", "СОВИНЬОН БЛАН", "SOVINON BLAN", "СОВИНЬОН-БЛАН"
    ],
    "ПИНО НУАР": [
        "PINOT NOIR", "PINOT", "NOIR", 
        "ПИНО НУАР", "ПИНО", "НУАР", 
        "PINO NUAR", "SPATBURGUNDER", "BLAUBURGUNDER", "SPÄTBURGUNDER"
    ],
    "ПИНО БЛАН": [
        "PINOT BLANC", "PINOT BIANCO", "WEISSBURGUNDER", 
        "ПИНО БЛАН", "PINO BLAN"
    ],
    "ПИНО ГРИ": [
        "PINOT GRIS", "PINOT GRIGIO", "GRAUBURGUNDER", 
        "ПИНО ГРИ", "ПИНО ГРИДЖО", "PINO GRI"
    ],
    "СИРА": [
        "SYRAH", "SHIRAZ", "СИРА", "ШИРАЗ", "SIRA", "SHIRAS"
    ],
    "РИСЛИНГ": [
        "RIESLING", "RHEINRIESLING", "РИСЛИНГ", "RISLING"
    ],
    "САПЕРАВИ": [
        "SAPERAVI", "САПЕРАВИ"
    ],
    "РКАЦИТЕЛИ": [
        "RKATSITELI", "RKACITELI", "РКАЦИТЕЛИ"
    ],
    "БАСТАРДО": [
        "BASTARDO", "БАСТАРДО", "БАСТАРДО МАГАРАЧСКИЙ"
    ],
    "КОКУР": [
        "KOKUR", "КОКУР", "КОКУР БЕЛЫЙ"
    ],
    "КРАСНОСТОП": [
        "KRASNOSTOP", "КРАСНОСТОП", "КРАСНОСТОП ЗОЛОТОВСКИЙ", "КРАСНОСТОП АНАПСКИЙ"
    ],
    "МУСКАТ": [
        "MUSCAT", "MOSCATO", "MUSKAT", "МУСКАТ", "МУСКАТЕЛЬ", "MUSCATEL", "MUSKATEL"
    ],
    "АЛИГОТЕ": [
        "ALIGOTE", "АЛИГОТЕ"
    ],
    "ТЕМПРАНИЛЬО": [
        "TEMPRANILLO", "ТЕМПРАНИЛЬО"
    ],
    "МАЛЬБЕК": [
        "MALBEC", "МАЛЬБЕК"
    ],
    "ВИОНЬЕ": [
        "VIOGNIER", "ВИОНЬЕ"
    ],
    "ГЕВЮРЦТРАМИНЕР": [
        "GEWURZTRAMINER", "GEWÜRZTRAMINER", "TRAMINER", "ГЕВЮРЦТРАМИНЕР", "ТРАМИНЕР"
    ],
    "ДОСТОЙНЫЙ": [
        "DOSTOYNY", "DOSTOYNYY", "ДОСТОЙНЫЙ"
    ],
    "АМУРСКИЙ ПОТАПЕНКО": [
        "AMURSKIY", "AMURSKY", "АМУРСКИЙ ПОТАПЕНКО", "ПОТАПЕНКО"
    ],
    "ЦИМЛЯНСКИЙ": [
        "TSIMLYANSKIY", "TSIMLYANSKY", "ЦИМЛЯНСКИЙ", "ЦИМЛЯНСКИЙ ЧЕРНЫЙ"
    ],
    "КЕФЕСИЯ": [
        "KEFESIYA", "КЕФЕСИЯ"
    ],
    "ГРЕНАШ": [
        "GRENACHE", "GARNACHA", "ГРЕНАШ", "ГАРНАЧА"
    ],
    "МАРСЕЛАН": [
        "MARSELAN", "МАРСЕЛАН"
    ],
    "СЕНСО": [
        "CINSAULT", "CINSAUT", "СЕНСО"
    ],
    "КАРМЕНЕР": [
        "CARMENERE", "CARMÉNÈRE", "КАРМЕНЕР"
    ],
    "ВЕРМЕНТИНО": [
        "VERMENTINO", "ВЕРМЕНТИНО"
    ],
    "ГРЮНЕР": [
        "GRUNER", "GRÜNER", "VELTLINER", "ГРЮНЕР", "ВЕЛЬТЛИНЕР"
    ],
    "ПТИ ВЕРДО": [
        "PETIT VERDOT", "ПТИ ВЕРДО"
    ],
    "БЬЯНКА": [
        "BIANCA", "БЬЯНКА", "БИАНКА"
    ],
    "АЛЕАТИКО": [
        "ALEATICO", "АЛЕАТИКО"
    ],
    "АРЕНИ": [
        "ARENI", "АРЕНИ"
    ],
    "БЛАУФРАНКИШ": [
        "BLAUFRANKISCH", "BLAUFRÄNKISCH", "БЛАУФРАНКИШ"
    ],
    "ЗИНФАНДЕЛЬ": [
        "ZINFANDEL", "ЗИНФАНДЕЛЬ"
    ],
    "ИЗАБЕЛЛА": [
        "ISABELLA", "ИЗАБЕЛЛА"
    ],
    "МАЛЬВАЗИЯ": [
        "MALVASIA", "МАЛЬВАЗИЯ"
    ],
    "МОНТЕПУЛЬЧАНО": [
        "MONTEPULCIANO", "МОНТЕПУЛЬЧАНО"
    ],
    "МУРВЕДР": [
        "MOURVEDRE", "MOURVÈDRE", "МУРВЕДР", "MONASTRELL"
    ],
    "КАБЕРНЕ КОРТИС": [
        "CABERNET CORTIS", "КАБЕРНЕ КОРТИС", "КАБЕРНЕ-КОРТИС", "CORTIS", "КОРТИС"
    ],
    "СИБИРЬКОВЫЙ": [
        "SIBIRKOVIY", "SIBIRKOVY", "SIBIRKOVIJ", "СИБИРЬКОВЫЙ", "СИБИРЬКОВЫ"
    ],
}

# 2. ОНТОЛОГИЯ ЦВЕТА
COLOR_ONTOLOGY = {
    "красное": {
        "КРАСНОЕ", "КРАСНЫЙ", "КРАСНАЯ", "КРАСНЫЕ", "RED", "ROUGE", "ROSSO", "TINTO", "ROT", "ROTWEIN", "KRASNOE", "KRASNYY", "KRASNAYA"
    },
    "белое": {
        "БЕЛОЕ", "БЕЛЫЙ", "БЕЛАЯ", "БЕЛЫЕ", "WHITE", "BLANC", "BIANCO", "BLANCO", "BRANCO", "WEISS", "WEISSWEIN", "BELOE", "BELYY", "BELAYA"
    },
    "розовое": {
        "РОЗОВОЕ", "РОЗОВЫЙ", "РОЗОВАЯ", "РОЗОВЫЕ", "РОЗЕ", "ROSE", "ROSÉ", "ROZÉ", "ROS", "ROSADO", "ROSATO", "BLUSH", "ROZOVOE", "ROZOVYY", "ROZOVAYA"
    },
}

# 3. ОНТОЛОГИЯ СЛАДОСТИ / САХАРА
SWEETNESS_ONTOLOGY = {
    "сухое": {
        "СУХОЕ", "СУХОЙ", "СУХАЯ", "СУХИЕ", "DRY", "SEC", "SECO", "SECCO", "TROCKEN", "BRUT", "БРЮТ", "SUHOE", "SUHOY"
    },
    "полусухое": {
        "ПОЛУСУХОЕ", "ПОЛУСУХОЙ", "ПОЛУСУХАЯ", "SEMI-DRY", "SEMIDRY", "DEMI-SEC", "DEMISEC", 
        "HALBTROCKEN", "POLUSUHOE", "POLUSUHOY", "ABBOCCATO", "OFF-DRY"
    },
    "полусладкое": {
        "ПОЛУСЛАДКОЕ", "ПОЛУСЛАДКИЙ", "ПОЛУСЛАДКАЯ", "SEMI-SWEET", "SEMISWEET", "MEDIUM SWEET", 
        "LIEBLICH", "AMABILE", "POLUSLADKOE", "POLUSLADKIY", "MOELLEUX"
    },
    "сладкое": {
        "СЛАДКОЕ", "СЛАДКИЙ", "СЛАДКАЯ", "SWEET", "DOUX", "DOLCE", "DULCE", "SUSS", "SÜSS", 
        "SLADKOE", "SLADKIY", "DESSERT", "ДЕСЕРТНОЕ", "ДЕСЕРТНЫЙ", "ЛИКЕРНОЕ", "ЛИКЕРНЫЙ"
    },
}

# 4. СПЕЦИАЛЬНЫЕ ЛИНЕЙКИ И ТЕРМИНЫ
SPECIAL_WINE_TERMS = {
    "RESERVE": {
        "RESERVE", "RESERVA", "RISERVA", "РЕЗЕРВ", "REZERV", "RESERV",
        "СЕМЕЙНЫЙ", "SEMEYNYY", "СЕМЕЙСТВО", "FAMILY", "FAMILY RESERVE"
    },
    "CUVEE": {"CUVEE", "CUVÉE", "КЮВЕ", "KYUVE"},
    "BLANC_DE_BLANCS": {"BLANC DE BLANCS", "BLANC DE BLANC", "БЛАН ДЕ БЛАН"},
    "BLANC_DE_NOIRS": {"BLANC DE NOIRS", "BLANC DE NOIR", "БЛАН ДЕ НУАР"},
    "SPARKLING": {"SPARKLING", "SPUMANTE", "CHAMPAGNE", "ШАМПАНСКОЕ", "ИГРИСТОЕ"},
    "PREMIUM": {"PREMIUM", "ПРЕМИУМ"},
    "SELECTION": {"SELECTION", "СЕЛЕКШН", "СЕЛЕКЦИЯ", "WINEMAKERS SELECTION"},
    "LIMITED": {"LIMITED", "ЛИМИТЕД", "ЛИМИТИРОВАННАЯ", "LIMITED EDITION"},
    "ESTATE": {"ESTATE", "ЭСТЕЙТ"},
    "CRU": {"CRU", "КРЮ", "GRAND CRU", "ГРАН КРЮ"},
    "BERRY_EXPLOSION": {"BERRY EXPLOSION", "ЯГОДНЫЙ ВЗРЫВ", "BERRY", "ЯГОДНЫЙ"},
    "FRUIT_EXPLOSION": {"FRUIT EXPLOSION", "ФРУКТОВЫЙ ВЗРЫВ", "FRUIT", "ФРУКТОВЫЙ"},
    "PERFEKT_KLASSIK": {"PERFEKT KLASSIK", "PERFECT CLASSIC", "ПЕРФЕКТ КЛАССИК"},
    "GUBERNATORSKOE": {"ГУБЕРНАТОРСКОЕ", "GUBERNATORSKOE"},
    "AVTORSKAYA_TEHNOLOGIYA": {"АВТОРСКАЯ ТЕХНОЛОГИЯ", "МОНО", "MONO"},
    "BRUT": {"BRUT", "БРЮТ", "BRYUT", "EXTRA BRUT", "ЭКСТРА БРЮТ"},
    "ENDEMY": {"ЭНДЕМЫ", "ENDEMY", "ЭНДЕМЬ", "ЭНДЕМИ"},
}

# 5. ОНТОЛОГИЯ БРЕНДОВ И ТЕРРУАРОВ (BRAND & TERROIR ONTOLOGY)
BRAND_TERROIR_SYNONYMS = {
    "СИКОРЫ": {"СИКОРЫ", "SIKORY", "СЕМИГОРЬЕ", "SEMIGORYE"},
    "ИНКЕРМАН": {"ИНКЕРМАН", "INKERMAN", "ИНКЕРМАНСКИЙ", "INKERMANSKIY", "ЗМВ"},
    "МЫСХАКО": {"МЫСХАКО", "MYSHAKO"},
    "ТАЛЮ": {"ТАЛЮ", "TALU", "ШАТО ДЕ ТАЛЮ", "CHATEAU DE TALU"},
    "ГОЛУБИЦКОЕ": {"ГОЛУБИЦКОЕ", "GOLUBITSKOE", "GOLUBITSKOYE"},
    "АЛЬМА": {"ALMA", "VALLEY", "АЛЬМА", "ВЭЛЛИ"},
    "МАРКОТХ": {"МАРКОТХ", "MARKOTKH"},
    "ГАЙ-КОДЗОР": {"ГАЙ КОДЗОР", "ГАЙ-КОДЗОР", "GAI KODZOR", "GAI-KODZOR", "ГАЙКОДЗОР"},
    "ДВА_ПЕТРА": {"TWO PETERS", "ДВА ПЕТРА", "TWO", "PETERS", "ДВА", "ПЕТРА"},
    "ЛИТАВЩУК": {"ЛИТАВЩУК", "LITAVSHCHUK", "ЛИТАВЩУКОВ"},
    "ВЕДЕРНИКОВ": {"ВЕДЕРНИКОВ", "ВЕДЕРНИКОВЪ", "VEDERNIKOV"},
    "УЗУНОВ": {"УЗУНОВ", "UZUNOV"},
    "БАТРАК": {"БАТРАК", "BATRAK"},
}

# Быстрый обратный поиск: Токен термина -> Канонический концепт
SPECIAL_TERM_LOOKUP = {v: k for k, vars_set in SPECIAL_WINE_TERMS.items() for v in vars_set}
BRAND_SYN_LOOKUP = {syn: canon for canon, syns in BRAND_TERROIR_SYNONYMS.items() for syn in syns}

# Множество всех отдельных слов сортов для фильтрации названий вин
ALL_GRAPE_WORDS = {w for variants in GRAPE_ONTOLOGY.values() for v in variants for w in v.split()}

# Гомоглифы для исправления артефактов смешанных кирилло-латинских шрифтов в OCR
HOMOGLYPH_CYR = {
    'H': 'Н', 'C': 'С', 'P': 'Р', 'B': 'В', 'X': 'Х', 
    'A': 'А', 'E': 'Е', 'O': 'О', 'T': 'Т', 'M': 'М', 'K': 'К', 'Y': 'У'
}


def extract_grape_concepts(text: str) -> set[str]:
    """
    Каноническое извлечение сортов винограда из текстового описания (поля базы или слага).
    Сначала проверяет полные составные фразы ('Каберне Фран', 'Совиньон Блан'),
    затем изолированные однословные сорта.
    """
    text_u = (text or "").upper()
    found = set()
    # 1. Многословные фразы
    for canonical, variants in GRAPE_ONTOLOGY.items():
        for v in variants:
            if " " in v or "-" in v:
                if v in text_u:
                    found.add(canonical)
                    break
    # 2. Однословные термины
    if not found:
        for canonical, variants in GRAPE_ONTOLOGY.items():
            for v in variants:
                if " " not in v and "-" not in v and len(v) >= 4:
                    if re.search(r"\b" + re.escape(v) + r"\b", text_u):
                        found.add(canonical)
                        break
    return found


def normalize_ocr_text(text: str) -> tuple[set[str], str, str]:
    """
    Возвращает:
    1. Множество очищенных отдельных слов (с удалением краевой пунктуации)
    2. Сплошную строку со словами через пробел для подстрок
    3. Сжатую строку без пробелов для поиска разреженного кернинга ('KA Б Е P H E')
       с автоматическим объединением кирилло-латинских гомоглифов.
    """
    import unicodedata
    t_clean = (text or "").replace("₽", "Р").replace("€", "Е").replace("$", "S")
    # Снятие диакритических знаков с латиницы (é -> e, è -> e, ô -> o, à -> a, ç -> c и т.д.):
    t_clean = "".join(c for c in unicodedata.normalize("NFKD", t_clean) if unicodedata.category(c) != "Mn")
    raw_tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", t_clean)
    words = {t.upper() for t in raw_tokens if len(t) >= 2}
    joined = " " + " ".join(sorted(words)) + " "
    compact = re.sub(r"[^A-Za-zА-Яа-яЁё0-9]", "", t_clean).upper()
    compact_cyr = "".join(HOMOGLYPH_CYR.get(ch, ch) for ch in compact)
    compact_all = f"{compact} {compact_cyr}"
    return words, joined, compact_all


def match_term_in_ocr(term: str, ocr_words: set[str], ocr_joined: str, ocr_compact: str) -> bool:
    """Универсальная мультиязычная проверка наличия термина в OCR."""
    t_u = term.upper()
    # 1. Точное слово
    if t_u in ocr_words:
        return True
    # 2. Фраза из нескольких слов в OCR
    if " " in t_u and t_u in ocr_joined:
        return True
    # 3. Разреженный кернинг (без пробелов)
    t_compact = re.sub(r"[^A-Za-zА-Яа-яЁё0-9]", "", t_u)
    if len(t_compact) >= 4 and t_compact in ocr_compact:
        return True
    # 4. Нечеткое совпадение для длинных слов (>= 5 символов)
    if len(t_u) >= 5:
        for o in ocr_words:
            if len(o) >= 4 and abs(len(o) - len(t_u)) <= 2:
                if difflib.SequenceMatcher(None, t_u, o).ratio() >= 0.82:
                    return True
    return False
