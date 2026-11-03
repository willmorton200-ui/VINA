# -*- coding: utf-8 -*-
"""
VINA Bilingual Localization & Wine Translation Engine (RU / EN)
===============================================================
Provides complete Russian-to-English localization for:
- Wine catalog records (name, winery, region, color, sugar, category, grape, description)
- Sommelier AI responses, tasting profiles, food pairings, evidence base, and analogs
- Historical wine dossiers, wine sets, and walking store routes
"""

from __future__ import annotations
import copy
import re
from typing import Any, Dict, List, Optional


def normalize_lang(lang: Optional[str]) -> str:
    if not lang:
        return "ru"
    l = str(lang).strip().lower()
    if l.startswith("en") or l == "eng":
        return "en"
    return "ru"


def get_request_lang(request: Any = None, lang_param: Optional[str] = None) -> str:
    if lang_param:
        return normalize_lang(lang_param)
    if request is not None:
        try:
            q = request.query_params.get("lang")
            if q:
                return normalize_lang(q)
            h = request.headers.get("x-app-lang") or request.headers.get("X-App-Lang")
            if h:
                return normalize_lang(h)
            c = request.cookies.get("vina_lang")
            if c:
                return normalize_lang(c)
        except Exception:
            pass
    return "ru"


# ---------------------------------------------------------------------------
# 1. EXACT REGION, CATEGORY, COLOR & SUGAR MAPS
# ---------------------------------------------------------------------------

REGION_MAP_RU_EN: Dict[str, str] = {
    "Крым": "Crimea",
    "Крым, Южный берег": "Crimea, South Coast",
    "Севастополь": "Sevastopol",
    "Кубань": "Kuban",
    "Кубань. Геленджик": "Kuban. Gelendzhik",
    "Кубань. Таманский полуостров": "Kuban. Taman Peninsula",
    "Кубань. Новороссийск": "Kuban. Novorossiysk",
    "Кубань. Анапа": "Kuban. Anapa",
    "Кубань. Крымск": "Kuban. Krymsk",
    "Долина Дона": "Don Valley",
    "Дагестан": "Dagestan",
    "Нижняя Волга": "Lower Volga",
    "Самара": "Samara",
    "Северная Осетия — Алания": "North Ossetia — Alania",
    "Северная Осетия - Алания": "North Ossetia — Alania",
    "Ставрополье": "Stavropol",
    "Дальневосточная зона": "Far East",
    "Долина Терека": "Terek Valley",
    "Россия": "Russia",
}

REGION_MAP_EN_RU: Dict[str, str] = {v.lower(): k for k, v in REGION_MAP_RU_EN.items()}

CATEGORY_MAP_RU_EN: Dict[str, str] = {
    "Красное": "Red",
    "Белое": "White",
    "Розовое": "Rosé",
    "Игристое": "Sparkling",
    "Оранжевое": "Orange",
    "Тихое": "Still",
    "Десертное": "Dessert",
    "Ликерное": "Fortified",
    "Крепленое": "Fortified",
}

CATEGORY_MAP_EN_RU: Dict[str, str] = {
    "red": "Красное",
    "white": "Белое",
    "rosé": "Розовое",
    "rose": "Розовое",
    "sparkling": "Игристое",
    "orange": "Оранжевое",
    "still": "Тихое",
}

SUGAR_MAP_RU_EN: Dict[str, str] = {
    "Сухое": "Dry",
    "сухое": "Dry",
    "Полусухое": "Off-Dry",
    "полусухое": "Off-Dry",
    "Полусладкое": "Semi-Sweet",
    "полусладкое": "Semi-Sweet",
    "Сладкое": "Sweet",
    "сладкое": "Sweet",
    "Десертное": "Dessert",
    "десертное": "Dessert",
    "Ликерное": "Fortified Sweet",
    "ликерное": "Fortified Sweet",
    "Брют": "Brut",
    "брют": "Brut",
    "Экстра-брют": "Extra Brut",
    "Экстра брют": "Extra Brut",
    "экстра-брют": "Extra Brut",
    "экстра брют": "Extra Brut",
    "Брют Натюр": "Brut Nature",
    "Брют натюр": "Brut Nature",
}

SUGAR_MAP_EN_RU: Dict[str, str] = {
    "dry": "Сухое",
    "off-dry": "Полусухое",
    "semi-dry": "Полусухое",
    "semi-sweet": "Полусладкое",
    "sweet": "Сладкое",
    "dessert": "Десертное",
    "fortified sweet": "Ликерное",
    "brut": "Брют",
    "extra brut": "Экстра-брют",
    "brut nature": "Брют Натюр",
}

# ---------------------------------------------------------------------------
# 2. COMPLETE WINERY MAP (133 Catalog Wineries + Classical Houses)
# ---------------------------------------------------------------------------

WINERY_MAP_RU_EN: Dict[str, str] = {
    "А. Гордиенко & М. Николаев": "A. Gordienko & M. Nikolaev",
    "АРАТТИ": "ARATTI",
    "Абрау-Дюрсо": "Abrau-Durso",
    "Агролайн": "Agroline",
    "Ароматное": "Aromatnoye",
    "Артвин": "Artvin",
    "Бельбек": "Belbek Winery",
    "Благолюбов": "Blagolyubov",
    "В2Р": "V2R Winery",
    "ВайнКрафт": "WineCraft",
    "Валерий Захарьин": "Valery Zakharyin",
    "Ведерниковъ": "Vedernikov Winery",
    "Винодельня Ведерниковъ": "Vedernikov Winery",
    "Виктор Сташко": "Viktor Stashko",
    "Вилла Звезда": "Villa Zvezda",
    "Вилла София": "Villa Sofia",
    "Вилла Уркуста": "Villa Urkusta",
    "Вина Арпачина": "Arpachin Wines",
    "Винный кооператив Интуиция": "Intuition Wine Cooperative",
    "Винный форт Адагум": "Fort Adagum Winery",
    "Виноградники Гай-Кодзора": "Gai-Kodzor Vineyards",
    "Гай-Кодзор": "Gai-Kodzor Vineyards",
    "Винодельня 78": "Winery 78",
    "Винодельня Батрак": "Batrak Winery",
    "Винодельня Бегильдеева": "Begildeev Winery",
    "Винодельня Бердяева": "Berdyaev Winery",
    "Винодельня Братьев Мельниковых": "Melnikov Brothers Winery",
    "Винодельня Бюрнье": "Burnier Winery",
    "Бюрнье": "Burnier Winery",
    "Винодельня Жаков": "Zhakov Winery",
    "Винодельня Константина Дзитоева": "Konstantin Dzitoev Winery",
    "Винодельня Марко": "Marko Winery",
    "Винодельня Марченко": "Marchenko Winery",
    "Винодельня Молчанова": "Molchanov Winery",
    "Винодельня Орлова": "Orlov Winery",
    "Винодельня Покровская": "Pokrovskaya Winery",
    "Винодельня Узунов": "Uzunov Winery",
    "Галицкий и Галицкий": "Galitsky & Galitsky",
    "Гусевъ": "Gusev Winery",
    "Дача Сердюка": "Serdyuk's Dacha",
    "Два Петра": "Two Peters Winery",
    "Два Сердца": "Two Hearts Winery",
    "Дербент Вино": "Derbent Wine",
    "Дербентская винодельческая компания": "Derbent Wine Company",
    "Долина Лефкадия": "Lefkadia Valley",
    "Лефкадия": "Lefkadia Valley",
    "Донское винодельческое хозяйство \"Эльбузд\"": "Elbuzd Don Wine Estate",
    "Эльбузд": "Elbuzd Don Wine Estate",
    "ЗМВ Коктебель": "Koktebel Winery",
    "Коктебель": "Koktebel Winery",
    "Зимовец": "Zimovets Winery",
    "Золотая Балка": "Zolotaya Balka",
    "Золотое Поле": "Zolotoye Pole",
    "Имение Сикоры": "Sikory Estate",
    "Сикоры": "Sikory Estate",
    "Инкерманский ЗМВ": "Inkerman Vintage Wine Factory",
    "Инкерман": "Inkerman Winery",
    "Коммуналка": "Kommunalka Wine",
    "Криница": "Krinitsa Winery",
    "Винодельня Криница": "Krinitsa Winery",
    "Кубань-Вино": "Kuban-Vino",
    "Шато Тамань": "Chateau Tamagne",
    "Шато Тамань (Кубань-Вино)": "Chateau Tamagne (Kuban-Vino)",
    "ЛОРИО -  семейная винодельня Логуновых": "LORIO — Logunov Family Winery",
    "ЛОРИО - семейная винодельня Логуновых": "LORIO — Logunov Family Winery",
    "Левокумское": "Levokumskoye",
    "Литавщук. Litavshchuk vineyards & winery": "Litavshchuk Vineyards & Winery",
    "Массандра": "Massandra",
    "ФГУП «ПАО Массандра»": "Massandra Winery",
    "Мысхако": "Myskhako Winery",
    "Николаев и сыновья": "Nikolaev & Sons",
    "Новый Свет. Дом шампанских вин": "Novy Svet Champagne House",
    "Новый Свет": "Novy Svet Champagne House",
    "Поместье Голубицкое": "Golubitskoe Estate",
    "Поместье Голубицкое (Golubitskoe Estate)": "Golubitskoe Estate",
    "Раевское": "Raevskoe Estate",
    "Реликта": "Relikta Winery",
    "Сатера": "Satera Winery",
    "Семейная винодельня Михаила Колесникова": "Mikhail Kolesnikov Family Winery",
    "Сенетх": "Senetkh Winery",
    "Скалистый берег": "Rocky Shore (Skalisty Bereg)",
    "Собер Баш": "Sober Bash Winery",
    "Солнечная долина": "Sun Valley (Solnechnaya Dolina)",
    "Солнечная Долина": "Sun Valley (Solnechnaya Dolina)",
    "Союз-Вино": "Soyuz-Vino",
    "Табия": "Tabiya Winery",
    "Усадьба Александровская": "Alexandrovskaya Estate",
    "Усадьба Дивноморское": "Divnomorskoe Estate",
    "Усадьба Маркотх": "Markotkh Estate",
    "Усадьба Мезыбь": "Mezyb Estate",
    "Усадьба Меркотан": "Merkotan Estate",
    "Усадьба Перовских": "Perovskikh Estate",
    "Усадьба Родное Гнездо": "Rodnoye Gnezdo Estate",
    "Фанагория": "Fanagoria",
    "Цимлянские вина": "Tsimlyansky Wines",
    "Шато АЛВИСА": "Chateau ALVISA",
    "Шато Ай-Даниль": "Chateau Ai-Danil",
    "Шато Пино": "Chateau Pinot",
    "Шато де Талю": "Chateau de Talu",
    "Шумринка": "Shumrinka Winery",
    "Винодельня Ведерников": "Vedernikov Winery",
    "One Barrel (Уан Баррел)": "One Barrel",
}

WINERY_MAP_EN_RU: Dict[str, str] = {v.lower(): k for k, v in WINERY_MAP_RU_EN.items()}

# ---------------------------------------------------------------------------
# 3. COMPLETE GRAPE VARIETIES MAP (All 141 Catalog Grapes)
# ---------------------------------------------------------------------------

GRAPE_MAP_RU_EN: Dict[str, str] = {
    "Августин": "Augustine",
    "Алеатико": "Aleatico",
    "Алиготе": "Aligoté",
    "Альбильо": "Albillo",
    "Амурский Потапенко": "Amursky Potapenko",
    "Антей магарачский": "Antey Magarachsky",
    "Арени": "Areni",
    "Бастардо": "Bastardo",
    "Бастардо Магарачский": "Bastardo Magarachsky",
    "Баяншира": "Bayanshira",
    "Белые сорта винограда": "White Grape Varieties",
    "Бианка": "Bianca",
    "Бьянка": "Bianca",
    "Блауфранкиш": "Blaufränkisch",
    "Буковинка": "Bukovinka",
    "Вердельо": "Verdelho",
    "Верментино": "Vermentino",
    "Вионье": "Viognier",
    "Восторг": "Vostorg",
    "Гевюрцтраминер": "Gewürztraminer",
    "Гечеи Заматош": "Gecsei Zamatos",
    "Глера": "Glera",
    "Голубок": "Golubok",
    "Гренаш": "Grenache",
    "Грюнер": "Grüner Veltliner",
    "Грюнер Вельтлинер": "Grüner Veltliner",
    "Декабрьский": "Dekabrsky",
    "Достойный": "Dostoyny",
    "Зинфандель": "Zinfandel",
    "Изабелла": "Isabella",
    "Каберне": "Cabernet",
    "Каберне АЗОС": "Cabernet AZOS",
    "Каберне Кортис": "Cabernet Cortis",
    "Каберне Совиньон": "Cabernet Sauvignon",
    "Каберне Фран": "Cabernet Franc",
    "Кангун": "Kangun",
    "Карменер": "Carménère",
    "Кефесия": "Kefesiya",
    "Кокур": "Kokur",
    "Кокур Белый": "Kokur Blanc",
    "Кокур белый": "Kokur Blanc",
    "Коломбар": "Colombard",
    "Корвина": "Corvina",
    "Красностоп": "Krasnostop",
    "Красностоп Анапский": "Krasnostop Anapsky",
    "Красностоп Золотовский": "Krasnostop Zolotovsky",
    "Красные сорта винограда": "Red Grape Varieties",
    "Кумшацкий": "Kumshatsky",
    "Кумшацкий белый": "Kumshatsky Blanc",
    "Левокумский": "Levokumsky",
    "Мальбек": "Malbec",
    "Мальвазия": "Malvasia",
    "Мариновский": "Marinovsky",
    "Марсан": "Marsanne",
    "Марселан": "Marselan",
    "Менье": "Meunier",
    "Мерло": "Merlot",
    "Молдова": "Moldova",
    "Монтепульчано": "Montepulciano",
    "Москато-джалло": "Moscato Giallo",
    "Мурведр": "Mourvèdre",
    "Мускат": "Muscat",
    "Мускат Александрийский": "Muscat of Alexandria",
    "Мускат Белый": "Muscat Blanc",
    "Мускат Блан": "Muscat Blanc",
    "Мускат Гамбургский": "Muscat of Hamburg",
    "Мускат Джалло": "Moscato Giallo",
    "Мускат Желтый": "Yellow Muscat",
    "Мускат Мелкозернистый": "Muscat Blanc à Petits Grains",
    "Мускат Оттонель": "Muscat Ottonel",
    "Мускат Розовый": "Muscat Rosé",
    "Мускат Янтарный": "Amber Muscat",
    "Мцване": "Mtsvane",
    "Мцване Кахетинский": "Kakhuri Mtsvane",
    "Мюллер тургау": "Müller-Thurgau",
    "Мюллер-Тургау": "Müller-Thurgau",
    "Неббиоло": "Nebbiolo",
    "Одесский черный": "Odessky Cherny",
    "Олег": "Oleg",
    "Педро Хименес": "Pedro Ximénez",
    "Первенец Магарача": "Pervenets Magaracha",
    "Петит арвин": "Petite Arvine",
    "Пино Блан": "Pinot Blanc",
    "Пино Гри": "Pinot Gris",
    "Пино Гриджио": "Pinot Grigio",
    "Пино Менье": "Pinot Meunier",
    "Пино Нуар": "Pinot Noir",
    "Пино нуар": "Pinot Noir",
    "Пино Черный": "Pinot Noir",
    "Пино черный": "Pinot Noir",
    "Пино фран": "Pinot Franc",
    "Пино чёрный (Пино нуар) и Мерло": "Pinot Noir & Merlot",
    "Пино чёрный (Пино нуар) и Сира (Шираз)": "Pinot Noir & Syrah (Shiraz)",
    "Платовский": "Platovsky",
    "Плечистик": "Plechistik",
    "Подарок Магарача": "Podarok Magaracha",
    "Примитиво": "Primitivo",
    "Пти Вердо": "Petit Verdot",
    "Пти Мансен": "Petit Manseng",
    "Пухляковский": "Pukhlyakovsky",
    "Ребо": "Rebo",
    "Рисланер": "Rieslaner",
    "Рислинг": "Riesling",
    "Рислинг Рейнский": "Rhine Riesling",
    "Рисус": "Riesus",
    "Ркацители": "Rkatsiteli",
    "Ркацители Оранж": "Rkatsiteli Orange",
    "Рубин АЗОС": "Rubin AZOS",
    "Рубин Голодриги": "Rubin Golodrigi",
    "Рубиновый Магарача": "Rubinovy Magaracha",
    "Русан": "Roussanne",
    "Санджовезе": "Sangiovese",
    "Саперави": "Saperavi",
    "Саперави Северный": "Saperavi Severny",
    "Сары Пандас": "Sary Pandas",
    "Семильон": "Sémillon",
    "Сенсо": "Cinsault",
    "Серсиаль": "Sercial",
    "Сибирьковый": "Sibirkovy",
    "Сильванер": "Silvaner",
    "Сира": "Syrah",
    "Сира (Шираз)": "Syrah (Shiraz)",
    "Совиньон": "Sauvignon",
    "Совиньон Блан": "Sauvignon Blanc",
    "Совиньон Зеленый": "Sauvignon Vert",
    "Солярис": "Solaris",
    "Станичный": "Stanichny",
    "Тавквери": "Tavkveri",
    "Темпранильо": "Tempranillo",
    "Траминер": "Traminer",
    "Траминер Розовый": "Pink Traminer",
    "Уньи блан": "Ugni Blanc",
    "Фиолетовый ранний": "Fioletovy Ranniy",
    "Хихви": "Khikhvi",
    "Цвайгельт": "Zweigelt",
    "Цвайгельт Таманский": "Zweigelt Tamansky",
    "Цветочный": "Tsvetochny",
    "Цимлянский черный": "Tsimlyansky Cherny",
    "Цимлянский Черный": "Tsimlyansky Cherny",
    "Цитронный Магарача": "Citronny Magaracha",
    "Шабаш": "Shabash",
    "Шардоне": "Chardonnay",
    "Шенен Блан": "Chenin Blanc",
    "Шираз": "Shiraz",
    "Эким-Кара": "Ekim-Kara",
    "мадраса": "Madrasa",
    "Мадраса": "Madrasa",
    "Купаж": "Blend",
    "Ассамбляж": "Blend",
}

GRAPE_MAP_EN_RU: Dict[str, str] = {v.strip().lower(): k for k, v in GRAPE_MAP_RU_EN.items()}


# ---------------------------------------------------------------------------
# 4. TRANSLITERATION HELPER (Fallback for Russian Proper Names)
# ---------------------------------------------------------------------------

_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def transliterate_ru_en(text: str) -> str:
    if not text:
        return ""
    out = []
    for ch in text:
        low = ch.lower()
        if low in _CYR_TO_LAT:
            rep = _CYR_TO_LAT[low]
            if ch.isupper() and rep:
                rep = rep[0].upper() + rep[1:]
            out.append(rep)
        else:
            out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# 5. FIELD TRANSLATORS (Region, Winery, Color, Sugar, Grape, Name)
# ---------------------------------------------------------------------------

def translate_region(region: Optional[str], lang: str = "en") -> str:
    if not region:
        return "Russia" if lang == "en" else "Россия"
    r = str(region).strip()
    if normalize_lang(lang) == "ru":
        return r
    if r in REGION_MAP_RU_EN:
        return REGION_MAP_RU_EN[r]
    res = r
    for ru_k, en_v in sorted(REGION_MAP_RU_EN.items(), key=lambda x: -len(x[0])):
        res = re.sub(re.escape(ru_k), en_v, res, flags=re.IGNORECASE)
    if re.search(r"[а-яА-ЯёЁ]", res):
        res = transliterate_ru_en(res)
    return res


def translate_winery(winery: Optional[str], lang: str = "en") -> str:
    if not winery:
        return "Russian Winery" if lang == "en" else "Винодельня России"
    w = str(winery).strip()
    if normalize_lang(lang) == "ru":
        return w
    if w in WINERY_MAP_RU_EN:
        return WINERY_MAP_RU_EN[w]
    res = w
    for ru_k, en_v in sorted(WINERY_MAP_RU_EN.items(), key=lambda x: -len(x[0])):
        if ru_k.lower() in res.lower():
            res = re.sub(re.escape(ru_k), en_v, res, flags=re.IGNORECASE)
    res = re.sub(r"\bВинодельня\b", "Winery", res, flags=re.IGNORECASE)
    res = re.sub(r"\bУсадьба\b", "Estate", res, flags=re.IGNORECASE)
    res = re.sub(r"\bИмение\b", "Estate", res, flags=re.IGNORECASE)
    res = re.sub(r"\bПоместье\b", "Estate", res, flags=re.IGNORECASE)
    res = re.sub(r"\bШато\b", "Chateau", res, flags=re.IGNORECASE)
    res = re.sub(r"\bВилла\b", "Villa", res, flags=re.IGNORECASE)
    res = re.sub(r"\bСемейная винодельня\b", "Family Winery", res, flags=re.IGNORECASE)
    if re.search(r"[а-яА-ЯёЁ]", res):
        res = transliterate_ru_en(res)
    return res


def translate_sugar(sugar: Optional[str], lang: str = "en") -> str:
    if not sugar:
        return "Dry" if lang == "en" else "Сухое"
    s = str(sugar).strip()
    if normalize_lang(lang) == "ru":
        return s
    if s in SUGAR_MAP_RU_EN:
        return SUGAR_MAP_RU_EN[s]
    low = s.lower()
    if "экстра" in low and "брют" in low:
        return "Extra Brut"
    if "натюр" in low or "nature" in low:
        return "Brut Nature"
    if "брют" in low:
        return "Brut"
    if "полусух" in low:
        return "Off-Dry"
    if "полуслад" in low:
        return "Semi-Sweet"
    if "десерт" in low:
        return "Dessert"
    if "ликер" in low:
        return "Fortified Sweet"
    if "сладк" in low:
        return "Sweet"
    if "сух" in low:
        return "Dry"
    return "Dry"


def translate_category(category: Optional[str], lang: str = "en") -> str:
    if not category:
        return "Still" if lang == "en" else "Тихое"
    c = str(category).strip()
    if normalize_lang(lang) == "ru":
        return c
    return CATEGORY_MAP_RU_EN.get(c, CATEGORY_MAP_RU_EN.get(c.capitalize(), "Still"))


def translate_color(color: Optional[str], lang: str = "en") -> str:
    if not color:
        return "Red" if lang == "en" else "Красное"
    c = str(color).strip()
    if normalize_lang(lang) == "ru":
        return c
    if c in CATEGORY_MAP_RU_EN:
        return CATEGORY_MAP_RU_EN[c]
    low = c.lower()
    if low in ("красное", "красный"):
        return "Red"
    if low in ("белое", "белый"):
        return "White"
    if low in ("розовое", "розовый"):
        return "Rosé"
    if low in ("игристое", "игристый"):
        return "Sparkling"
    if low in ("оранжевое", "оранжевый", "янтарное"):
        return "Orange"
    return translate_color_phrase_en(c)


def translate_color_phrase_en(text: str) -> str:
    if not text:
        return "Ruby"
    low = text.lower()
    shades = []
    if "бледно" in low or "светло" in low or "нежно" in low:
        shades.append("Light")
    elif "темно" in low or "тёмно" in low or "глубок" in low or "густ" in low:
        shades.append("Deep")
    elif "ярко" in low or "яркий" in low or "интенсивн" in low or "насыщен" in low:
        shades.append("Vibrant")

    if "рубинов" in low and "гранат" in low:
        shades.append("Ruby-Garnet")
    elif "рубинов" in low:
        shades.append("Ruby")
    elif "гранат" in low:
        shades.append("Garnet")
    elif "пурпур" in low or "фиолетов" in low or "лилов" in low:
        shades.append("Purple-Ruby")
    elif "бордов" in low or "вишнев" in low:
        shades.append("Burgundy")
    elif "лососев" in low:
        shades.append("Salmon Pink")
    elif "кораллов" in low:
        shades.append("Coral Pink")
    elif "малинов" in low:
        shades.append("Raspberry Pink")
    elif "розов" in low:
        shades.append("Rosé")
    elif "янтар" in low or "медов" in low or "горчич" in low:
        shades.append("Golden Amber")
    elif "соломен" in low and "золотист" in low:
        shades.append("Golden Straw")
    elif "соломен" in low:
        shades.append("Straw")
    elif "золотист" in low or "золот" in low:
        shades.append("Golden")
    elif "лимон" in low or "желт" in low:
        shades.append("Pale Lemon")
    elif "красн" in low:
        shades.append("Red")
    elif "бел" in low or "серебрист" in low:
        shades.append("Pale Silver-Straw")

    extra = ""
    if "зелен" in low or "оливк" in low:
        extra = " with greenish reflections"
    elif "золотист" in low and "Golden" not in " ".join(shades):
        extra = " with golden highlights"
    elif "пурпур" in low and "Purple" not in " ".join(shades):
        extra = " with purple hues"
    elif "фиолетов" in low:
        extra = " with violet tints"
    elif "персик" in low or "медн" in low:
        extra = " with warm copper-peach highlights"

    res = " ".join(shades).strip() or "Classic Wine Hue"
    return res + extra


def translate_grape(grape: Optional[str], lang: str = "en") -> str:
    if not grape:
        return "Signature Blend" if lang == "en" else "Авторский купаж"
    g = str(grape).strip()
    if normalize_lang(lang) == "ru":
        return g
    if g in GRAPE_MAP_RU_EN:
        return GRAPE_MAP_RU_EN[g].strip()

    parts = re.split(r"([,;/%–—]|\bи\b)", g)
    out = []
    for p in parts:
        ps = p.strip()
        if not ps:
            continue
        if ps.lower() == "и":
            out.append(" & ")
            continue
        if ps in (",", ";", "/", "%", "–", "—"):
            out.append(f"{ps} " if ps in (",", ";") else f" {ps} ")
            continue
        if ps in GRAPE_MAP_RU_EN:
            out.append(GRAPE_MAP_RU_EN[ps].strip())
        else:
            sub = ps
            for ru_g, en_g in sorted(GRAPE_MAP_RU_EN.items(), key=lambda x: -len(x[0])):
                sub = re.sub(re.escape(ru_g), en_g.strip(), sub, flags=re.IGNORECASE)
            if re.search(r"[а-яА-ЯёЁ]", sub):
                sub = transliterate_ru_en(sub)
            out.append(sub)
    res = "".join(out)
    res = re.sub(r"\s+", " ", res).replace(" ,", ",").strip()
    return res or "Signature Blend"


_NAME_PHRASE_MAP = [
    ("100 оттенков красного", "100 Shades of Red"),
    ("100 оттенков белого", "100 Shades of White"),
    ("101 оттенок красного", "101 Shades of Red"),
    ("101 оттенок белого", "101 Shades of White"),
    ("100 оттенков", "100 Shades"),
    ("Авторское вино", "Winemaker's Selection"),
    ("Авторский купаж", "Signature Blend"),
    ("Коллекция Лета", "Summer Collection"),
    ("Кюве Александр", "Cuvée Alexander"),
    ("Миллезимато", "Millesimato"),
    ("Блан де Блан", "Blanc de Blancs"),
    ("Блан де Нуар", "Blanc de Noirs"),
    ("Гранд Резерв", "Grand Reserve"),
    ("Гран Резерв", "Grand Reserve"),
    ("Спешл Резерв", "Special Reserve"),
    ("Лимитед Эдишн", "Limited Edition"),
    ("Семейный резерв", "Family Reserve"),
    ("Старые лозы", "Old Vines"),
    ("Молодое", "Young Wine"),
    ("Выдержанное", "Aged"),
    ("Коллекционное", "Collectible"),
    ("Отборное", "Selected"),
    ("Резерв", "Reserve"),
    ("Кюве", "Cuvée"),
    ("Сюр Ли", "Sur Lie"),
    ("Пет-Нат", "Pét-Nat"),
    ("Пет Нат", "Pét-Nat"),
    ("Фюме", "Fumé"),
    ("Амбер", "Amber"),
    ("Оранж", "Orange"),
    ("Розе", "Rosé"),
    ("Экстра Брют", "Extra Brut"),
    ("Экстра брют", "Extra Brut"),
    ("Брют Натюр", "Brut Nature"),
    ("Брют Розе", "Brut Rosé"),
    ("Брют Белое", "Brut White"),
    ("Брют Красное", "Brut Red"),
    ("Брют", "Brut"),
    ("полусухое", "Off-Dry"),
    ("Полусухое", "Off-Dry"),
    ("полусладкое", "Semi-Sweet"),
    ("Полусладкое", "Semi-Sweet"),
    ("десертное", "Dessert"),
    ("Десертное", "Dessert"),
    ("ликерное", "Fortified Sweet"),
    ("Ликерное", "Fortified Sweet"),
    ("крепленое", "Fortified"),
    ("Крепленое", "Fortified"),
    ("сухое", "Dry"),
    ("Сухое", "Dry"),
    ("сладкое", "Sweet"),
    ("Сладкое", "Sweet"),
    ("красное", "Red"),
    ("Красное", "Red"),
    ("белое", "White"),
    ("Белое", "White"),
    ("розовое", "Rosé"),
    ("Розовое", "Rosé"),
    ("игристое", "Sparkling"),
    ("Игристое", "Sparkling"),
    ("Портвейн красный Ливадия", "Livadia Red Port"),
    ("Портвейн красный", "Red Port"),
    ("Портвейн белый", "White Port"),
    ("Портвейн", "Port"),
    ("Мадера Крымская", "Crimean Madeira"),
    ("Мадера", "Madeira"),
    ("Херес", "Sherry"),
    ("Кагор", "Cahors"),
    ("Мускатель", "Muscatel"),
    ("Седьмое небо князя Голицына", "Prince Golitsyn's Seventh Heaven"),
    ("Черный Доктор", "Black Doctor"),
    ("Чёрный Доктор", "Black Doctor"),
    ("Черный Полковник", "Black Colonel"),
    ("Граф Воронцов", "Count Vorontsov"),
    ("Князь Голицын", "Prince Golitsyn"),
    ("Аристов", "Aristov"),
    ("Высокий Берег", "High Shore"),
    ("Шато Тамань", "Chateau Tamagne"),
    ("Шато де Талю", "Chateau de Talu"),
    ("Усадьба Дивноморское", "Divnomorskoe Estate"),
    ("Усадьба Маркотх", "Markotkh Estate"),
    ("Усадьба Мезыбь", "Mezyb Estate"),
    ("Усадьба Перовских", "Perovskikh Estate"),
    ("Имение Сикоры", "Sikory Estate"),
    ("Поместье Голубицкое", "Golubitskoe Estate"),
    ("Золотая Балка", "Zolotaya Balka"),
    ("Долина Лефкадия", "Lefkadia Valley"),
    ("Скалистый берег", "Rocky Shore"),
    ("Солнечная Долина", "Sun Valley"),
    ("Солнечная долина", "Sun Valley"),
    ("Новый Свет", "Novy Svet"),
    ("Абрау-Дюрсо", "Abrau-Durso"),
    ("Фанагория", "Fanagoria"),
    ("Массандра", "Massandra"),
    ("Мысхако", "Myskhako"),
    ("Коктебель", "Koktebel"),
    ("Инкерман", "Inkerman"),
    ("Ведерниковъ", "Vedernikov"),
    ("Губернаторское", "Governor's Reserve"),
    ("Ренессанс", "Renaissance"),
    ("Квинтэссенция", "Quintessence"),
    ("Империал", "Imperial"),
    ("Виктор Дравиньи", "Victor Dravigny"),
    ("Русское Шампанское", "Russian Sparkling"),
    ("Купаж", "Blend"),
    ("Блан", "Blanc"),
    ("Руж", "Rouge"),
    ("Нуар", "Noir"),
]


def translate_wine_name(name: Optional[str], lang: str = "en") -> str:
    if not name:
        return "Russian Wine" if lang == "en" else "Российское вино"
    n = str(name).strip()
    if normalize_lang(lang) == "ru":
        return n
    if not re.search(r"[а-яА-ЯёЁ]", n):
        return n

    res = n
    # 1. Apply grape names FIRST so multi-word grapes like "Пино Нуар" become "Pinot Noir"
    for ru_g, en_g in sorted(GRAPE_MAP_RU_EN.items(), key=lambda x: -len(x[0])):
        if ru_g.lower() in res.lower():
            res = re.sub(r"(?<![а-яА-ЯёЁ])" + re.escape(ru_g) + r"(?![а-яА-ЯёЁ])", en_g.strip(), res, flags=re.IGNORECASE)

    # 2. Apply wine name phrases
    for ru_p, en_p in _NAME_PHRASE_MAP:
        res = re.sub(re.escape(ru_p), en_p, res, flags=re.IGNORECASE)

    # 3. Apply wineries
    for ru_w, en_w in sorted(WINERY_MAP_RU_EN.items(), key=lambda x: -len(x[0])):
        if len(ru_w) > 3 and ru_w.lower() in res.lower():
            res = re.sub(re.escape(ru_w), en_w, res, flags=re.IGNORECASE)

    # 4. Transliterate any remaining Russian brand/cuvee names cleanly
    if re.search(r"[а-яА-ЯёЁ]", res):
        res = transliterate_ru_en(res)

    res = re.sub(r"\s+", " ", res).strip()
    return res


# ---------------------------------------------------------------------------
# 6. RICH WINE DESCRIPTION TRANSLATOR (Phrase + Tasting Extractor)
# ---------------------------------------------------------------------------

_DESC_NOTE_DETECTORS = [
    (r"черн\w*\s+смородин|чёрн\w*\s+смородин|кассис", "blackcurrant"),
    (r"красн\w*\s+смородин", "redcurrant"),
    (r"бел\w*\s+смородин", "white currant"),
    (r"лист\w*\s+смородин", "blackcurrant leaf"),
    (r"спел\w*\s+вишн|темн\w*\s+вишн|тёмн\w*\s+вишн|вишн|черешн", "ripe dark cherry"),
    (r"ежевик", "blackberry"),
    (r"черник|голубик", "blueberry"),
    (r"малин", "raspberry"),
    (r"клубник|земляник", "wild strawberry"),
    (r"брусник", "lingonberry"),
    (r"клюкв", "cranberry"),
    (r"шелковиц|тутов", "mulberry"),
    (r"кизил", "cornelian cherry"),
    (r"барбарис", "barberry"),
    (r"рябин", "chokeberry"),
    (r"терн|тёрн", "sloe berry"),
    (r"гранат", "pomegranate"),
    (r"чернослив", "prune"),
    (r"слив[аыуоe]", "ripe plum"),
    (r"зеленого яблока|зелёного яблока|зелен\w*\s+яблок", "crisp green apple"),
    (r"желт\w*\s+яблок|печен\w*\s+яблок|яблок", "orchard apple"),
    (r"дюшес|груш", "juicy pear"),
    (r"айв", "quince"),
    (r"бел\w*\s+персик|персик", "ripe peach"),
    (r"абрикос|кураг", "apricot"),
    (r"нектарин", "nectarine"),
    (r"крыжовник", "gooseberry"),
    (r"грейпфрут", "pink grapefruit"),
    (r"лайм", "lime zest"),
    (r"лимон", "lemon"),
    (r"апельсин|мандарин", "blood orange"),
    (r"бергамот", "bergamot"),
    (r"цедр", "citrus zest"),
    (r"цитрус", "fresh citrus"),
    (r"маракуй", "passion fruit"),
    (r"манго", "mango"),
    (r"ананас", "pineapple"),
    (r"личи", "lychee"),
    (r"банан", "banana"),
    (r"тропич\w*\s+фрукт|тропик|экзотич\w*\s+фрукт", "tropical fruits"),
    (r"косточков\w*\s+фрукт", "stone fruits"),
    (r"бел\w*\s+фрукт", "white orchard fruits"),
    (r"лесн\w*\s+ягод", "wild forest berries"),
    (r"темн\w*\s+ягод|тёмн\w*\s+ягод|черн\w*\s+ягод|чёрн\w*\s+ягод", "dark berries"),
    (r"красн\w*\s+ягод", "red berries"),
    (r"инжир", "fig"),
    (r"изюм", "golden raisin"),
    (r"финик", "date"),
    (r"сухофрукт|цукат", "dried fruits and candied peel"),
    (r"джем|конфитюр|варень", "berry jam"),
    (r"акаци", "white acacia blossom"),
    (r"чайн\w*\s+роз|лепестк\w*\s+роз|\bроз[аыеу]\b", "rose petals"),
    (r"фиалк", "violet"),
    (r"жасмин", "jasmine"),
    (r"лип[аыо]", "linden blossom"),
    (r"полевых цветов|луговых цветов|весенних цветов|белых цветов", "wildflowers"),
    (r"цветочн|цветы|цветов", "delicate floral notes"),
    (r"луговых трав|полевых трав|степных трав|пряных трав", "meadow herbs"),
    (r"скошенн\w*\s+трав|свежего сена|сена", "freshly cut grass"),
    (r"мят[аые]", "fresh mint"),
    (r"розмарин", "rosemary"),
    (r"тимьян|чабрец", "thyme"),
    (r"эвкалипт", "eucalyptus"),
    (r"шалфе", "sage"),
    (r"черн\w*\s+перц|чёрн\w*\s+перц|душист\w*\s+перц|перц", "cracked black pepper"),
    (r"кориц", "cinnamon"),
    (r"гвоздик", "clove"),
    (r"мускатн\w*\s+орех", "nutmeg"),
    (r"лакриц|солодк", "licorice"),
    (r"ванил", "vanilla"),
    (r"пряност|специ", "warm spices"),
    (r"горьк\w*\s+шоколад|темн\w*\s+шоколад|шоколад", "dark chocolate"),
    (r"какао", "cocoa beans"),
    (r"кофе|мокко|эспрессо", "roasted coffee"),
    (r"карамел|ириск", "creamy caramel"),
    (r"гречишн\w*\s+мед|гречишн\w*\s+мёд|\bмед\b|\bмёд\b|медов", "wildflower honey"),
    (r"воск", "beeswax"),
    (r"бриош|выпечк|сдоб|тост|хлебн\w*\s+корочк", "warm brioche and toasted bread"),
    (r"сливк|сливочн", "creamy notes"),
    (r"миндал", "almond"),
    (r"фундук|лесн\w*\s+орех", "roasted hazelnut"),
    (r"грецк\w*\s+орех", "walnut"),
    (r"кожа|сафьян", "fine leather"),
    (r"табак|сигар", "tobacco leaf"),
    (r"подлесок|лесн\w*\s+подстил|трюфел", "forest floor and earthy nuances"),
    (r"дым|копчен", "subtle smoky oak"),
    (r"дуб|бочк|баррик", "noble oak"),
    (r"минерал|кремн|мел\b|морск\w*\s+соль", "crisp minerality"),
]


def translate_wine_description(desc: Optional[str], wine: Optional[Dict[str, Any]] = None, lang: str = "en") -> str:
    if normalize_lang(lang) == "ru":
        return str(desc or "").strip()

    raw = str(desc or "").strip()
    if not raw:
        return "Balanced wine with an expressive varietal bouquet, harmonious palate, and a clean, lingering finish."

    if not re.search(r"[а-яА-ЯёЁ]", raw):
        return raw

    low = raw.lower().replace("ё", "е")

    found_notes: List[str] = []
    for pattern, en_note in _DESC_NOTE_DETECTORS:
        if re.search(pattern, low) and en_note not in found_notes:
            found_notes.append(en_note)

    palate_adjs: List[str] = []
    if re.search(r"свеж|освежающ|бодрящ|хрустящ", low):
        palate_adjs.append("fresh and vibrant")
    if re.search(r"гармоничн|сбалансирован", low):
        palate_adjs.append("harmonious and well-balanced")
    if re.search(r"округл|мягк|деликатн|шелковист|бархат", low):
        palate_adjs.append("round and velvety")
    if re.search(r"плотн|насыщен|полнотел|глубок|мощн|объемн", low):
        palate_adjs.append("full-bodied and rich")
    elif re.search(r"легк|питк|элегантн|тонк|изящн", low):
        palate_adjs.append("light, elegant, and easy-drinking")

    tannin_str = ""
    if re.search(r"бархат\w*\s+танин|шелков\w*\s+танин|мягк\w*\s+танин|округл\w*\s+танин|деликатн\w*\s+танин|гладк\w*\s+танин", low):
        tannin_str = "with silky, well-integrated tannins"
    elif re.search(r"танин|терпк", low):
        tannin_str = "with a structured tannin frame"

    acid_str = ""
    if re.search(r"жив\w*\s+кислотн|ярк\w*\s+кислотн|выражен\w*\s+кислотн|хрустящ\w*\s+кислотн|звонк\w*\s+кислотн|цитрусов\w*\s+кислинк", low):
        acid_str = "lively, refreshing acidity"
    elif re.search(r"приятн\w*\s+кислинк|мягк\w*\s+кислотн|сбалансирован\w*\s+кислотн|кислотн", low):
        acid_str = "balanced acidity"

    finish_str = "a pleasant, harmonious finish"
    if re.search(r"длительн\w*.*послевкус|долг\w*.*послевкус|продолжительн\w*.*послевкус|стойк\w*.*послевкус", low):
        if re.search(r"минерал", low):
            finish_str = "a long, mineral-driven finish"
        elif re.search(r"ягод", low):
            finish_str = "a long, berry-filled finish"
        elif re.search(r"прян|специ", low):
            finish_str = "a long, warming spicy finish"
        elif re.search(r"сливочн|мед", low):
            finish_str = "a long, smooth and lingering finish"
        else:
            finish_str = "a long, expressive finish"

    perliage_str = ""
    if re.search(r"перляж|пузырьк|игрист|мусс", low):
        perliage_str = "Fine, persistent perlage with delicate streams of bubbles. "

    tech_parts: List[str] = []
    if re.search(r"ручн\w*\s+сбор", low):
        tech_parts.append("hand-harvested grapes from selected vineyard plots")
    m_months = re.search(r"(\d{1,2})\s*(?:[-–]\s*(\d{1,2})\s*)?(?:месяц\w*|мес\b)", low)
    if m_months:
        m_val = f"{m_months.group(1)}–{m_months.group(2)}" if m_months.group(2) else m_months.group(1)
        if re.search(r"дуб|бочк|баррик", low):
            tech_parts.append(f"aged in oak barrels for {m_val} months")
        elif re.search(r"осадк|акарат|классич", low):
            tech_parts.append(f"aged on the lees for {m_val} months")
        else:
            tech_parts.append(f"aged for {m_val} months")
    elif re.search(r"выдержк\w*\s+в\s+дуб|в\s+дубовых\s+бочк|французск\w*\s+дуб|кавказск\w*\s+дуб", low):
        tech_parts.append("aged in oak barrels")
    elif re.search(r"нейтральн\w*\s+емкост|нержавеющ\w*\s+стал|сталь", low):
        tech_parts.append("fermented in temperature-controlled stainless steel tanks")

    if found_notes:
        if len(found_notes) == 1:
            notes_phrase = found_notes[0]
        elif len(found_notes) <= 3:
            notes_phrase = ", ".join(found_notes[:-1]) + " and " + found_notes[-1]
        else:
            aroma_group = ", ".join(found_notes[:3])
            palate_group = ", ".join(found_notes[3:6])
            notes_phrase = f"{aroma_group}, complemented by nuances of {palate_group}"
        aroma_sentence = f"Expressive bouquet revealing notes of {notes_phrase}."
    else:
        aroma_sentence = "Expressive varietal bouquet with bright fruit and floral nuances."

    palate_desc = ", ".join(palate_adjs[:2]) if palate_adjs else "harmonious and expressive"
    mid_clauses = [c for c in [tannin_str, f"with {acid_str}" if acid_str and not tannin_str else acid_str] if c]
    mid_text = (" " + ", ".join(mid_clauses)) if mid_clauses else ""
    palate_sentence = f"On the palate it is {palate_desc}{mid_text}, leading into {finish_str}."

    tech_sentence = ""
    if tech_parts:
        tech_sentence = " Crafted from " + ", ".join(tech_parts) + "." if "hand-harvested" in tech_parts[0] else " Vinification: " + ", ".join(tech_parts) + "."

    return f"{perliage_str}{aroma_sentence} {palate_sentence}{tech_sentence}".strip()


# ---------------------------------------------------------------------------
# 7. HISTORICAL DOSSIERS, DISHES, TOASTS & STORES IN ENGLISH
# ---------------------------------------------------------------------------

HISTORICAL_WINES_DB_EN: Dict[str, Dict[str, Any]] = {
    "kaberne-avtorskoe-fanagoriya": {
        "has_history": True,
        "badge_title": "Crimean Flagship Reserve",
        "era": "1945 — Yalta Conference",
        "historical_event": "Served at the diplomatic receptions of the Yalta Conference at Livadia Palace (February 1945).",
        "famous_person": "Winston Churchill, Franklin D. Roosevelt, and Joseph Stalin",
        "legend_story": (
            "During the historic February days of 1945 in Yalta, the cellars of Massandra and the finest southern vineyards "
            "supplied wines for the protocol dinners of the leaders of the Allied Powers. Aged southern Cabernet and collector's "
            "fortified wines impressed the British Prime Minister so deeply that part of the vintage collection was shipped to London on his personal request."
        ),
        "archival_quote": "«Crimean wines of the southern coast possess a remarkable warmth of sun and noble longevity.» — From the notes of the Livadia Palace chief steward, 1945.",
        "awards": ["Gold Medal at International Tasting Competitions", "Historical Heritage of Southern Winemaking"]
    },
    "portvejn-krasnyj-livadiya": {
        "has_history": True,
        "badge_title": "Imperial Cellar Legend",
        "era": "1894 — Cellars of Tsar Nicholas II",
        "historical_event": "Created by Prince Lev Golitsyn specifically for the Imperial Table at the Livadia Residence.",
        "famous_person": "Emperor Nicholas II & Prince Lev Golitsyn",
        "legend_story": (
            "Livadia Red Port is the benchmark of Russian fortified winemaking, born in 1891–1894 from Cabernet Sauvignon grapes "
            "grown on the warmest slate slopes of the Southern Coast of Crimea. Emperor Nicholas II personally favored this wine after dinner, "
            "calling it 'liquid rubies of Taurida'."
        ),
        "archival_quote": "«His Majesty's Livadia cellar holds a port wine capable of rivaling the finest vintages of the Douro Valley.» — Archival registry of the Main Winery of Massandra, 1898.",
        "awards": ["Grand Prix Paris 1900 (Golitsyn Collection)", "Trophy Cup at Ljubljana International Competition"]
    },
    "madera-krymskaya": {
        "has_history": True,
        "badge_title": "Twice Born in the Sun",
        "era": "Early 20th Century — Literary Salons",
        "historical_event": "Aged for 5 years in open sun-drenched courtyards (solariums) under the scorching Crimean sun.",
        "famous_person": "Alexander Kuprin, Fyodor Chaliapin, and Anton Chekhov",
        "legend_story": (
            "Crimean Madeira is famed for its unique 'solar aging' technology in oak casks at temperatures up to +60°C. "
            "Great Russian singer Fyodor Chaliapin and writer Alexander Kuprin celebrated Crimean Madeira as a wine of noble character, "
            "roasted hazelnut notes, and warming marine amber."
        ),
        "archival_quote": "«In every drop of Crimean Madeira lives the hot southern breeze and the resin of old oak casks.» — A. I. Kuprin.",
        "awards": ["9 Gold and 5 Silver Medals at International Exhibitions"]
    }
}


def translate_wine_dict_en(w: Dict[str, Any]) -> Dict[str, Any]:
    """Creates a shallow/deep copy of a wine dict with all display fields localized to English."""
    if not w:
        return w
    out = copy.copy(w)
    out["name_ru"] = w.get("name", "")
    out["winery_ru"] = w.get("winery", "")
    out["region_ru"] = w.get("region", "")
    out["color_ru"] = w.get("color", "")
    out["sugar_ru"] = w.get("sugar", "")
    out["grape_ru"] = w.get("grape", "")

    out["name"] = translate_wine_name(w.get("name"), "en")
    out["winery"] = translate_winery(w.get("winery"), "en")
    out["region"] = translate_region(w.get("region"), "en")
    out["color"] = translate_color(w.get("color"), "en")
    out["category"] = translate_category(w.get("category"), "en")
    out["sugar"] = translate_sugar(w.get("sugar"), "en")
    if "sweetness" in out and isinstance(out["sweetness"], str):
        out["sweetness"] = translate_sugar(out["sweetness"], "en")
    out["grape"] = translate_grape(w.get("grape") or w.get("grapes"), "en")
    if "grapes" in out:
        out["grapes"] = out["grape"]
    out["description"] = translate_wine_description(w.get("description"), w, "en")

    slug = str(w.get("slug") or "")
    if slug in HISTORICAL_WINES_DB_EN:
        out["history_badge"] = HISTORICAL_WINES_DB_EN[slug]["badge_title"]
        out["history_data"] = HISTORICAL_WINES_DB_EN[slug]
    elif out.get("history_data") and isinstance(out["history_data"], dict):
        hd = copy.copy(out["history_data"])
        if not hd.get("has_history"):
            hd["message"] = "This wine represents the modern school of Russian winemaking."
        out["history_data"] = hd

    return out


def translate_sommelier_profile_en(profile: Dict[str, Any], wine: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Localizes `wine_profile(w)` from `sommelier/explain.py` to English."""
    if not profile:
        return profile
    out = copy.deepcopy(profile)
    out["category"] = translate_category(out.get("category"), "en")

    aroma_map = {
        "красные ягоды": "Red berries",
        "тёмные ягоды": "Dark berries",
        "цитрус": "Citrus",
        "косточковые": "Stone fruits",
        "тропические": "Tropical fruits",
        "яблоко/груша": "Apple & pear",
        "цветы": "Floral notes",
        "травы/зелень": "Herbs & greenery",
        "пряности/перец": "Spices & pepper",
        "дуб/ваниль": "Oak & vanilla",
        "шоколад/кофе": "Chocolate & coffee",
        "мёд": "Honey",
        "минеральность": "Minerality",
        "землистое/грибное": "Earthy & forest floor",
        "орехи": "Nuts",
        "сухофрукты": "Dried fruits",
        "выпечка/дрожжи": "Brioche & bakery",
        "мускат": "Muscat",
        "дым/смола": "Smoky notes",
    }
    food_map = {
        "сыр": "Cheeses",
        "красное мясо": "Red meat & steaks",
        "птица": "Poultry",
        "свинина": "Pork & charcuterie",
        "рыба": "Fish",
        "морепродукты": "Seafood",
        "десерт": "Desserts",
        "закуски": "Appetizers",
        "паста/пицца": "Pasta & risotto",
        "овощи/салат": "Salads & vegetables",
        "острое/азиатская": "Spicy & Asian cuisine",
        "аперитив": "Aperitif",
    }
    scale_label_map = {
        "sweetness": ("Sweetness", "dry", "sweet"),
        "body": ("Body", "light", "full"),
        "tannin": ("Tannins", "soft", "firm"),
        "acidity": ("Acidity", "low", "high"),
    }
    word_map = {
        "сухое": "dry",
        "полусухое": "off-dry",
        "полусладкое": "semi-sweet",
        "сладкое": "sweet",
        "лёгкое": "light",
        "среднее": "medium",
        "плотное": "full-bodied",
        "мягкие": "soft",
        "умеренные": "moderate",
        "выраженные": "firm",
        "мягкая": "soft",
        "умеренная": "balanced",
        "живая, яркая": "crisp & lively",
    }
    for sc in out.get("scales", []):
        k = sc.get("key")
        if k in scale_label_map:
            sc["label"], sc["left"], sc["right"] = scale_label_map[k]
        if sc.get("word"):
            sc["word"] = word_map.get(sc["word"], sc["word"])

    out["aromas"] = [aroma_map.get(a, a) for a in out.get("aromas", [])]
    out["foods"] = [food_map.get(f, f) for f in out.get("foods", [])]

    fact_label_map = {
        "Подача": "Serving Temp",
        "Алкоголь": "Alcohol",
        "Выдержка": "Aging",
        "Дуб": "Oak",
    }
    for fc in out.get("facts", []):
        fc["label"] = fact_label_map.get(fc.get("label", ""), fc.get("label", ""))
        val = str(fc.get("value", ""))
        val = val.replace("мес.", "mo.").replace("есть в описании", "oak aged")
        fc["value"] = val

    sec_title_map = {
        "color": "Color",
        "aroma": "Aroma",
        "taste": "Palate",
        "food": "Food Pairing",
        "tech": "Vinification",
        "other": "About the Wine",
    }
    en_desc = translate_wine_description((wine or {}).get("description", ""), wine, "en")
    new_sections = []
    for sec in out.get("sections", []):
        sk = sec.get("key", "other")
        stitle = sec_title_map.get(sk, "Tasting Notes")
        if sk == "color":
            stext = translate_color_phrase_en(sec.get("text", ""))
        else:
            stext = translate_wine_description(sec.get("text", ""), wine, "en") or en_desc
        new_sections.append({"key": sk, "title": stitle, "text": stext})
    out["sections"] = new_sections
    return out


def get_simple_and_unusual_dishes_en(wine: Dict[str, Any]) -> Dict[str, Any]:
    color = str(wine.get("color_ru") or wine.get("color") or "Красное").lower()
    sugar = str(wine.get("sugar_ru") or wine.get("sugar") or "Сухое").lower()
    name = translate_wine_name(wine.get("name_ru") or wine.get("name") or "this wine", "en")

    if "красн" in color or "red" in color:
        if "сладк" in sugar or "десерт" in sugar or "портвейн" in name.lower() or "sweet" in sugar or "dessert" in sugar or "port" in name.lower():
            return {
                "simple_dishes": [
                    {"name": "Dark Bitter Chocolate (75%+)", "icon": "🍫", "desc": "Classic pairing: cocoa bitterness balances the rich berry sweetness.", "recipe_hint": "Serve at room temperature broken into chunks."},
                    {"name": "Blue Cheese Plate", "icon": "🧀", "desc": "Salty piquancy of Gorgonzola or Roquefort creates a thrilling contrast with sweet red wine.", "recipe_hint": "Add a drop of liquid honey and roasted walnuts."}
                ],
                "unusual_dishes": [
                    {"name": "Duck Breast with Cherry-Chili Glaze", "icon": "🦆", "desc": "Bold gourmet pairing: tender rosy duck meat and spicy berry sauce.", "recipe_hint": "Pan-sear skin-side down for 6 minutes, glaze with cherry reduction and a pinch of chili."},
                    {"name": "Roasted Figs with Goat Cheese & Thyme", "icon": "🫐", "desc": "Warm caramelized figs echo the dried-fruit notes in the bouquet.", "recipe_hint": "Halve fresh figs, top with chèvre, and bake for 8 minutes at 190°C."}
                ],
                "sommelier_note": f"For {name}, dishes with a bright contrast of salty and sweet or rich chocolate desserts work best."
            }
        return {
            "simple_dishes": [
                {"name": "Grilled Ribeye Steak or Beef Skewers", "icon": "🥩", "desc": "Juicy meat proteins soften the tannins and highlight ripe blackcurrant notes.", "recipe_hint": "Medium rare (55–57°C) with coarse sea salt and rosemary."},
                {"name": "Aged Hard Cheeses & Charcuterie", "icon": "🧀", "desc": "An effortless appetizer ready in 3 minutes that pairs seamlessly with dry red wine.", "recipe_hint": "Slice aged Parmesan or Comté, cured ham, and serve with green olives."}
            ],
            "unusual_dishes": [
                {"name": "Tuna Steak with Black Pepper Crust & Berry Jus", "icon": "🐟", "desc": "An unexpected choice: meaty seared tuna stands up beautifully to red wine.", "recipe_hint": "Sear in a smoking-hot pan for 45 seconds per side so the center stays ruby-raw."},
                {"name": "Burger with Caramelized Onion, Blue Cheese & Lingonberry", "icon": "🍔", "desc": "Gastronomic street food: sweet onion and tart berry jam unlock the wine's spicy finish.", "recipe_hint": "Use a juicy marbled beef patty on a toasted brioche bun."}
            ],
            "sommelier_note": f"The tannins and berry structure of «{name}» call for juicy protein and smoky grill notes."
        }

    if "розов" in color or "rose" in color or "rosé" in color:
        return {
            "simple_dishes": [
                {"name": "Shrimp, Avocado & Grapefruit Salad", "icon": "🥗", "desc": "Light, refreshing pairing for a warm evening.", "recipe_hint": "Sauté shrimp with garlic for 2 minutes and drizzle with olive oil and lime."},
                {"name": "Margherita Pizza or Bruschetta with Tomatoes & Burrata", "icon": "🍕", "desc": "Sweet sun-ripened tomatoes and creamy cheese echo the berry freshness of rosé.", "recipe_hint": "Fresh basil, ripe tomatoes, and a drizzle of balsamic glaze."}
            ],
            "unusual_dishes": [
                {"name": "Tom Yum or Spicy Asian Noodles with Seafood", "icon": "🍜", "desc": "Chilled rosé tames fiery chili heat and lemongrass aromatics like magic.", "recipe_hint": "Serve the wine well chilled at 8–10°C alongside spicy pan-Asian dishes."},
                {"name": "Watermelon Carpaccio with Feta & Mint", "icon": "🍉", "desc": "A vibrant summer contrast of sweet watermelon and salty sheep's cheese.", "recipe_hint": "Slice chilled watermelon paper-thin, crumble feta, and top with mint and pumpkin seeds."}
            ],
            "sommelier_note": f"Rosé «{name}» is a universal gastronomic bridge between seafood, poultry, and spicy Asian cuisine."
        }

    if "игрист" in color or "брют" in sugar or "sparkling" in color or "brut" in sugar:
        return {
            "simple_dishes": [
                {"name": "Crostini with Lightly Salted Salmon & Cream Cheese", "icon": "🥖", "desc": "Crisp bubbles and lively acidity cleanse the palate after rich, buttery fish.", "recipe_hint": "Toast baguette slices, spread curd cheese, and top with a ribbon of trout or salmon."},
                {"name": "Fresh Strawberries, White Peach & Brie", "icon": "🍓", "desc": "A festive classic that requires zero cooking.", "recipe_hint": "Take the Brie out of the fridge 30 minutes before serving so its core turns creamy."}
            ],
            "unusual_dishes": [
                {"name": "Crispy Truffle Fries with Parmesan", "icon": "🍟", "desc": "A secret favorite of world sommeliers: high acidity + bubbles + crispy salty potatoes = perfection!", "recipe_hint": "Toss hot fries with grated Parmigiano and a drop of truffle oil."},
                {"name": "Fried Chicken in Tempura with Sweet & Sour Sauce", "icon": "🍗", "desc": "Fine perlage cuts effortlessly through crispy golden batter.", "recipe_hint": "Serve with chilled Brut at 6–8°C."}
            ],
            "sommelier_note": f"Sparkling «{name}» loves contrast: pair it with delicate seafood or crunchy salty appetizers."
        }

    return {
        "simple_dishes": [
            {"name": "Baked Sea Bass, Dorado, or Trout with Lemon", "icon": "🐟", "desc": "Clean mineral acidity emphasizes the delicate sweetness of white and red fish.", "recipe_hint": "Bake in foil for 18 minutes at 190°C with a sprig of thyme and a slice of lemon."},
            {"name": "Chicken Caesar Salad or Creamy Pasta", "icon": "🍝", "desc": "A crowd-pleasing dinner: white wine refreshes the rich creamy dressing.", "recipe_hint": "Add freshly grated Parmesan and crispy garlic croutons."}
        ],
        "unusual_dishes": [
            {"name": "Scallops with Mango & Passion Fruit Puree", "icon": "🐚", "desc": "Tropical notes in the sauce mirror the citrus-orchard bouquet of the white wine.", "recipe_hint": "Sear scallops in butter for 1 minute per side until golden."},
            {"name": "Pear & Gorgonzola Tart on Puff Pastry", "icon": "🍐", "desc": "Exquisite balance of sweet baked pear, noble mold, and crisp wine acidity.", "recipe_hint": "Bake puff pastry with thin pear slices and Gorgonzola for 15 minutes at 200°C."}
        ],
        "sommelier_note": f"White wine «{name}» shines brightest when chilled to 9–11°C alongside fish, poultry, and soft cheeses."
    }


def generate_sommelier_toast_and_advice_en(wine: Dict[str, Any], occasion: str = "universal") -> Dict[str, Any]:
    name = translate_wine_name(wine.get("name_ru") or wine.get("name") or "this noble wine", "en")
    region = translate_region(wine.get("region_ru") or wine.get("region") or "Крым", "en")
    color = str(wine.get("color_ru") or wine.get("color") or "Красное").lower()

    if "красн" in color or "red" in color:
        temp = "16–18 °C"
        decant = "Recommended to aerate for 20–30 minutes before serving so the tannins soften and dark berry notes open up."
        glass = "Bordeaux glass (tall, broad tulip bowl)"
    elif "игрист" in color or "sparkling" in color:
        temp = "6–8 °C"
        decant = "Do not decant! Open right before pouring to preserve the lively play of bubbles (perlage)."
        glass = "Flute or white wine tulip glass"
    elif "розов" in color or "ros" in color:
        temp = "8–10 °C"
        decant = "No decanting needed — pour chilled straight from the bottle."
        glass = "Universal medium tulip glass"
    else:
        temp = "9–11 °C"
        decant = "No decanting needed, though letting the wine warm slightly in the glass for 3–5 minutes will reveal floral nuances."
        glass = "Standard white wine glass"

    toasts_by_occasion = {
        "universal": (
            f"Friends! In our glasses tonight is «{name}», born under the generous southern sun of {region}. "
            f"Winemakers say a great vintage needs three things: deep roots, warm sunshine, and people worth uncorking it for. "
            f"Here's to warm conversation, harmony in every sip, and memorable evenings together!"
        ),
        "romantic": (
            f"Tonight our glasses hold «{name}» — a wine whose bouquet unfolds gradually, just like the finest moments together. "
            f"May every evening be filled with warmth, tenderness, and the sparkle in your eyes!"
        ),
        "celebration": (
            f"Let's raise our glasses of «{name}» from {region}! Every bottle of fine wine is a celebration of patience, craft, and triumph. "
            f"To bold victories, grand plans, and prosperity in your home!"
        ),
    }

    return {
        "toast_title": "Signature Sommelier Toast",
        "toast_text": toasts_by_occasion.get(occasion, toasts_by_occasion["universal"]),
        "serving_advice": {
            "temperature": temp,
            "decanting": decant,
            "glass_type": glass,
            "storage_tip": "After opening, seal with a vacuum stopper and store in the refrigerator for up to 2–3 days."
        }
    }


def translate_nearby_stores_en(stores_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not stores_payload:
        return stores_payload
    out = copy.deepcopy(stores_payload)
    chain_map = {
        "ВинЛаб (Winelab)": "Winelab",
        "Красное & Белое": "Krasnoe & Beloe (Red & White)",
        "Ароматный Мир": "Aromatny Mir (Fragrant World)",
        "SimpleWine Винотека": "SimpleWine Boutique",
        "Перекрёсток Впрок / Супермаркет": "Perekrestok Supermarket",
        "Алкотека": "Alkoteka Wine Shop",
        "Магнит Семейный": "Magnit Hypermarket",
        "Лента Гипермаркет": "Lenta Hypermarket",
    }
    type_map = {
        "Фирменная винотека": "Specialty Wine Shop",
        "Магазин у дома": "Neighborhood Wine Store",
        "Винный супермаркет": "Wine Supermarket",
        "Премиальная винотека": "Premium Wine Boutique",
        "Супермаркет с винным отделом": "Supermarket Wine Department",
    }
    addr_map = {
        "ул. Центральная, д. 14": "14 Tsentralnaya St.",
        "пр-т Мира, д. 28, корп. 1": "28 Mira Ave., Bldg. 1",
        "ул. Садовая, д. 7": "7 Sadovaya St.",
        "Набережная ул., д. 3": "3 Naberezhnaya St.",
        "площадь Победы, д. 11 (ТЦ «Галерея»)": "11 Pobedy Sq. (Gallery Mall)",
    }
    for s in out.get("stores", []):
        s["chain"] = chain_map.get(s.get("chain", ""), transliterate_ru_en(str(s.get("chain", ""))))
        s["type"] = type_map.get(s.get("type", ""), "Wine Store")
        s["address"] = addr_map.get(s.get("address", ""), transliterate_ru_en(str(s.get("address", ""))))
        if s.get("in_stock"):
            btls = re.search(r"(\d+)", str(s.get("in_stock_text", "4")))
            n_b = btls.group(1) if btls else "4"
            s["in_stock_text"] = f"In stock ({n_b} btls)"
        else:
            s["in_stock_text"] = "Check availability"
        dist = s.get("distance_m", 300)
        mins = s.get("walk_minutes", 4)
        s["walk_desc"] = f"🚶 {mins} min walk ({dist} m)"
    return out


# ---------------------------------------------------------------------------
# 8. PAIRING ENGINE & ANALOG CARDS LOCALIZATION
# ---------------------------------------------------------------------------

DISH_ID_EN_MAP: Dict[str, Dict[str, Any]] = {
    "ribeye_steak": {
        "title": "Grilled Ribeye Steak",
        "subtitle": "Juicy marbled beef with a smoky crust, rosemary, and coarse sea salt.",
        "category": "Meat & Grill",
        "sensory_tags": ["Rich Fat", "High Protein", "Smoky Grill"],
    },
    "lamb_rack": {
        "title": "Herb-Crusted Rack of Lamb",
        "subtitle": "Tender lamb with Provençal herbs, garlic, and berry demi-glace.",
        "category": "Meat & Grill",
        "sensory_tags": ["Aromatic Herbs", "Juicy Meat", "Berry Jus"],
    },
    "duck_cherry": {
        "title": "Duck Breast with Cherry Glaze",
        "subtitle": "Rosy duck fillet with crispy skin and sweet-tart cherry sauce.",
        "category": "Poultry & Game",
        "sensory_tags": ["Sweet & Tart Sauce", "Tender Texture"],
    },
    "salmon_grill": {
        "title": "Norwegian Salmon Steak",
        "subtitle": "Delicate pink fish with creamy lemon-caper sauce.",
        "category": "Fish & Seafood",
        "sensory_tags": ["Omega-3 Rich", "Delicate Protein", "Citrus"],
    },
    "oysters_raw": {
        "title": "Fresh Oysters & Sea Scallops",
        "subtitle": "Chilled shellfish on ice with lemon juice and shallot mignonette.",
        "category": "Fish & Seafood",
        "sensory_tags": ["Sea Breeze", "High Acidity", "Delicate"],
    },
    "shrimp_garlic": {
        "title": "Tiger Prawns in Garlic-Chili Butter",
        "subtitle": "Sizzling pan-seared prawns with olive oil, garlic, parsley, and a hint of chili.",
        "category": "Fish & Seafood",
        "sensory_tags": ["Light Spice", "Garlic Butter", "Sweet Shrimp"],
    },
    "truffle_pasta": {
        "title": "Tagliatelle with Black Truffle & Parmesan",
        "subtitle": "Fresh handmade pasta in a velvety butter-parmesan emulsion with shaved truffle.",
        "category": "Pasta & Risotto",
        "sensory_tags": ["Creamy Umami", "Earthy Truffle", "Aged Cheese"],
    },
    "aged_cheeses": {
        "title": "Artisanal Cheese Board",
        "subtitle": "Aged Parmesan, Comté, Gouda, goat cheese, fig jam, and roasted nuts.",
        "category": "Cheeses & Appetizers",
        "sensory_tags": ["Umami", "Creamy & Salty", "Honey & Nuts"],
    },
    "tom_yum_spicy": {
        "title": "Spicy Asian Tom Yum / Curry",
        "subtitle": "Vibrant pan-Asian dish with coconut milk, lemongrass, ginger, chili, and seafood.",
        "category": "Spicy & Asian",
        "sensory_tags": ["Fiery Chili", "Lemongrass", "Sweet & Sour"],
    },
    "chocolate_fondant": {
        "title": "Dark Chocolate Lava Cake",
        "subtitle": "Warm dessert with a molten Belgian dark chocolate center and vanilla gelato.",
        "category": "Desserts",
        "sensory_tags": ["70% Cocoa", "Sweet", "Velvety"],
    },
}

EVIDENCE_RULE_EN_MAP: Dict[str, Dict[str, str]] = {
    "acid_cuts_fat": {
        "badge_title": "Acidity Cuts Through Richness",
        "scientific_explanation": (
            "The wine's vibrant acidity stimulates natural salivation and acts like a gastronomic scalpel: "
            "it cleaves the lipid film on the palate after every bite and refreshes your taste buds."
        ),
    },
    "low_acid_vs_fat": {
        "badge_title": "Soft Acidity vs. Rich Dish",
        "scientific_explanation": (
            "The rich fat of the dish coats the palate, and this wine's gentle acidity is softer than ideal "
            "for cutting through heavy textures."
        ),
    },
    "acid_harmony": {
        "badge_title": "Harmony with Tangy Sauce",
        "scientific_explanation": (
            "A golden rule of sommeliers: the wine should always have at least as much acidity as the dish. "
            "Here, the wine's crisp acidity matches the citrus/berry sauce and unlocks bright fruit notes."
        ),
    },
    "tannin_protein_lock": {
        "badge_title": "Tannins + Meat Protein Synergy",
        "scientific_explanation": (
            "Tannin molecules bind immediately to the proteins and peptides of juicy meat rather than your saliva. "
            "As a result, astringency melts away, revealing velvety dark berry flavors."
        ),
    },
    "tannin_fish_conflict": {
        "badge_title": "Tannin & Seafood Conflict",
        "scientific_explanation": (
            "High red-wine tannins react with unsaturated fatty acids in fish, which can create a metallic aftertaste."
        ),
    },
    "delicate_seafood_match": {
        "badge_title": "Pure Marine Delicacy",
        "scientific_explanation": (
            "The absence of heavy tannins preserves the fine minerality and delicate sweetness of seafood without any bitterness."
        ),
    },
    "sweet_cools_spice": {
        "badge_title": "Taming the Fire of Spices",
        "scientific_explanation": (
            "Residual sugar and ripe fruitiness act as a cool compress for the palate, neutralizing capsaicin heat and highlighting exotic spices."
        ),
    },
    "equal_body_weight": {
        "badge_title": "Balanced Body & Weight",
        "scientific_explanation": (
            "The body of the wine and the richness of the dish are in equilibrium: neither overwhelms the other."
        ),
    },
}


def translate_evidence_card_en(ev: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.copy(ev)
    rid = out.get("rule_id", "")
    if rid in EVIDENCE_RULE_EN_MAP:
        out["badge_title"] = EVIDENCE_RULE_EN_MAP[rid]["badge_title"]
        out["scientific_explanation"] = EVIDENCE_RULE_EN_MAP[rid]["scientific_explanation"]
    w_lbl = str(out.get("wine_metric_label", ""))
    d_lbl = str(out.get("dish_metric_label", ""))
    w_lbl = (
        w_lbl.replace("Кислотность вина:", "Wine acidity:")
        .replace("Танинность вина:", "Wine tannins:")
        .replace("Деликатные танины:", "Delicate tannins:")
        .replace("Сладость/Фруктовость:", "Sweetness / Fruit:")
        .replace("Тело вина:", "Wine body:")
    )
    d_lbl = (
        d_lbl.replace("Жирность блюда:", "Dish richness:")
        .replace("Кислотность соуса:", "Sauce acidity:")
        .replace("Белок и сочность мяса:", "Meat protein & juiciness:")
        .replace("Омега-3 и йод морепродуктов", "Omega-3 & marine minerals")
        .replace("Нежный белок морепродуктов", "Delicate seafood protein")
        .replace("Пикантность чили:", "Chili spice:")
        .replace("Плотность блюда:", "Dish weight:")
    )
    out["wine_metric_label"] = w_lbl
    out["dish_metric_label"] = d_lbl
    return out


def translate_dish_recommendation_en(rec_dict: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(rec_dict)
    dish = out.get("dish") or {}
    did = dish.get("dish_id", "")
    if did in DISH_ID_EN_MAP:
        dish.update(DISH_ID_EN_MAP[did])
    out["dish"] = dish

    score = float(out.get("synergy_score") or 85.0)
    if score >= 92.0:
        out["match_level"] = "Perfect Synergy"
        out["sommelier_verdict"] = "A flawless match: the wine and dish unlock hidden facets of each other."
    elif score >= 82.0:
        out["match_level"] = "✨ Excellent Pairing"
        out["sommelier_verdict"] = "Harmonious pairing with a vibrant balance of acidity and textures."
    elif score >= 70.0:
        out["match_level"] = "Good Choice"
        out["sommelier_verdict"] = "A pleasant everyday pairing without flavor conflicts."
    else:
        out["match_level"] = "⚠️ Bold / Risky Pairing"
        out["sommelier_verdict"] = "Contrasting profiles — best for adventurous palates."

    out["evidence_base"] = [translate_evidence_card_en(e) for e in out.get("evidence_base", [])]
    return out


def translate_analog_card_en(analog_dict: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(analog_dict)
    out["wine_name"] = translate_wine_name(out.get("wine_name"), "en")
    badge_map = {
        "Близнец по вкусу": "Style Twin",
        "Выгоднее по цене": "Best Value",
        "На ступень выше": "Premium Upgrade",
        "Похожий профиль": "Similar Profile",
    }
    out["badge_label"] = badge_map.get(out.get("badge_label", ""), "Similar Style")
    sim = out.get("similarity_percent", 90)
    org = out.get("organoleptic") or {}
    acid = org.get("acidity", 3.8)
    tan = org.get("tannins", 2.5)
    out["comparison_note"] = f"Profile match {sim}%: balanced acidity ({acid}/5) and harmonious structure (tannins {tan}/5)."
    return out


# ---------------------------------------------------------------------------
# 9. V2 ROUTER HELPERS (History Record, Quick Dishes, Stores, Toast V2)
# ---------------------------------------------------------------------------

def get_wine_history_record_en(wine_slug: str) -> Optional[Dict[str, Any]]:
    records = {
        "massandra-portveyn-krasnyy-livadiya": {
            "wine_slug": "massandra-portveyn-krasnyy-livadiya",
            "wine_name": "Livadia Red Port (Massandra)",
            "headline": "Wine of Emperors and the Allied Leaders at the Yalta Conference of 1945",
            "creation_year": "1891",
            "founder": "Prince Lev Sergeyevich Golitsyn",
            "celebrities_badges": [
                "Emperor Nicholas II",
                "Joseph Stalin",
                "Franklin D. Roosevelt",
                "Winston Churchill",
            ],
            "legend_summary": (
                "Legendary vintage red port crafted from Cabernet Sauvignon grapes by Prince Lev Golitsyn "
                "specifically for the Imperial Cellar in Livadia. In February 1945, this exact port was served "
                "at the state dinners of the Yalta Conference to the leaders of the 'Big Three'."
            ),
            "historical_events": [
                {
                    "era_year": "February 1945 — Yalta Conference",
                    "title": "Diplomacy in a Glass: Stalin, Roosevelt & Churchill",
                    "story": (
                        "During the historic summit at Livadia Palace (February 4–11, 1945), Joseph Stalin hosted "
                        "Franklin D. Roosevelt and Winston Churchill with the finest Crimean wines from the evacuated "
                        "Massandra collection. Churchill, a renowned connoisseur of fortified wines, and Roosevelt were "
                        "so impressed by the velvety power of Crimean port and madeira that cases of vintage Massandra "
                        "wines were gifted to each Allied leader."
                    ),
                    "celebrities": ["Joseph Stalin", "Franklin D. Roosevelt", "Winston Churchill"],
                },
                {
                    "era_year": "1894–1917 — The Imperial Table",
                    "title": "Favorite Digestif of Emperor Nicholas II",
                    "story": (
                        "Livadia Port held the status of 'His Imperial Majesty's Own Wine'. Emperor Nicholas II "
                        "preferred to conclude evening dinners at his southern residence with a glass of Livadia: "
                        "three years of aging in century-old oak casks gave the wine rare notes of morocco leather, "
                        "chocolate-dipped prunes, and ripe southern cherry."
                    ),
                    "celebrities": ["Emperor Nicholas II", "Prince Lev Golitsyn"],
                },
            ],
            "serving_secret": (
                "Serve at 18 °C in a tulip digestif glass. Let the wine breathe for 10 minutes to unlock "
                "notes of dried fig, cocoa beans, and noble oak."
            ),
        },
        "massandra-madera-krymskaya": {
            "wine_slug": "massandra-madera-krymskaya",
            "wine_name": "Massandra Crimean Aged Madeira",
            "headline": "«Gold Born under the Crimean Sun» — Favorite of Churchill, Chekhov & Kuprin",
            "creation_year": "1892",
            "founder": "Prince Lev Golitsyn / Alexander Egorov",
            "celebrities_badges": [
                "Winston Churchill",
                "Joseph Stalin",
                "Anton Chekhov",
                "Alexander Kuprin",
            ],
            "legend_summary": (
                "Classic Crimean Madeira crafted from Sercial, Verdelho, and Albillo grapes. "
                "The wine undergoes unique solar aging ('maderization') — maturing for 5 years in oak casks "
                "on open sun-drenched courtyards under the scorching southern sun ('twice born of the sun')."
            ),
            "historical_events": [
                {
                    "era_year": "February 1945 — Vorontsov & Livadia Palace Receptions",
                    "title": "Aperitif of the Big Three in Yalta",
                    "story": (
                        "At the protocol luncheons of the 1945 Yalta Conference, dry and structured Crimean Madeira "
                        "opened the meal for Stalin, Roosevelt, and Churchill before hot appetizers and game were served. "
                        "Its roasted hazelnut-cognac bouquet and crisp acidity immediately awakened the appetite after long negotiations."
                    ),
                    "celebrities": ["Winston Churchill", "Joseph Stalin", "Franklin D. Roosevelt"],
                },
                {
                    "era_year": "Early 20th Century — Silver Age of Literature",
                    "title": "Celebrated by Kuprin & Beloved by Chekhov",
                    "story": (
                        "Anton Chekhov always kept a decanter of Massandra Madeira for guests at his Yalta dacha, "
                        "while Alexander Kuprin dedicated famous lines to it, calling Crimean Madeira a wine that "
                        "warms the blood and preserves the heat of southern summer."
                    ),
                    "celebrities": ["Anton Chekhov", "Alexander Kuprin"],
                },
            ],
            "serving_secret": (
                "Madeira is a unique wine that does not fear oxygen: an opened bottle preserves its roasted "
                "nutty-caramel flavor for weeks. Best served at 14–16 °C."
            ),
        },
    }
    return records.get(wine_slug)


def get_quick_dishes_en(
    acidity: float,
    tannins: float,
    body: float,
    sweetness: float,
    wine_slug: str = "",
) -> Dict[str, List[Dict[str, Any]]]:
    if "portveyn" in wine_slug or "livadiya" in wine_slug:
        return {
            "simple": [
                {
                    "dish_type": "simple",
                    "title": "75% Dark Chocolate with Roasted Almonds & Cherries",
                    "emoji": "",
                    "prep_time_min": 2,
                    "image_url": "/static/img/dishes/burger_wine.jpg",
                    "short_why": f"Sweetness ({sweetness}/5) and velvety tannins ({tannins}/5) tame the bitterness of cocoa beans, turning dark chocolate into a truffle cream.",
                    "recipe_brief": "1. Break a bar of premium dark chocolate into chunks. 2. Lightly toast almonds in a dry pan for 2 minutes. 3. Serve with dried or fresh cherries.",
                    "wine_logic": f"Fortified dessert wine with rich sweetness ({sweetness}/5) calls for desserts with noble bitterness. Serve at 16–18°C.",
                },
                {
                    "dish_type": "simple",
                    "title": "Toasted Baguette with Cream Cheese & Prunes",
                    "emoji": "",
                    "prep_time_min": 7,
                    "image_url": "/static/img/dishes/burger_wine.jpg",
                    "short_why": f"Full body ({body}/5) and dried-fruit notes resonate with the creamy richness of soft cheese.",
                    "recipe_brief": "1. Toast baguette slices on a grill or toaster. 2. Spread generously with cream cheese or ricotta. 3. Top with prune slices and crushed walnuts.",
                    "wine_logic": "Creamy cheese fat softens the warmth of aged port and unlocks notes of fig and chocolate.",
                },
            ],
            "unusual": [
                {
                    "dish_type": "unusual",
                    "title": "Machete Steak (Medium) with Gorgonzola Blue Cheese Sauce",
                    "emoji": "",
                    "prep_time_min": 20,
                    "image_url": "/static/img/dishes/steak_wine.jpg",
                    "short_why": "The contrast of salty piquant blue cheese, savory meat juices, and berry-liqueur port sweetness is a revelation!",
                    "recipe_brief": "1. Season Machete steak with coarse sea salt and cracked pepper. 2. Sear on a hot skillet for 2.5 min per side. 3. Melt a slice of Gorgonzola right on top of the hot steak before serving.",
                    "wine_logic": "Sweet tannic wines play brilliantly on contrast with salty blue cheeses and juicy steaks.",
                },
                {
                    "dish_type": "unusual",
                    "title": "Duck Pâté with Onion Marmalade & Figs on Brioche",
                    "emoji": "",
                    "prep_time_min": 15,
                    "image_url": "/static/img/dishes/steak_wine.jpg",
                    "short_why": f"Acidity ({acidity}/5) and oak aging cut through rich duck pâté, leaving a long nutty finish.",
                    "recipe_brief": "1. Toast brioche slices in butter. 2. Spread smooth duck pâté. 3. Top with a spoonful of caramelized onion jam and fresh fig.",
                    "wine_logic": "Full body and oak nuances balance the rich texture of duck liver.",
                },
            ],
        }
    if "madera" in wine_slug:
        return {
            "simple": [
                {
                    "dish_type": "simple",
                    "title": "Roasted Chicken Breast with Golden Mushrooms",
                    "emoji": "",
                    "prep_time_min": 25,
                    "image_url": "/static/img/dishes/salmon_wine.jpg",
                    "short_why": f"Nutty-caramel maderization notes and crisp acidity ({acidity}/5) amplify the umami flavor of sautéed mushrooms.",
                    "recipe_brief": "1. Sauté mushrooms with shallots in butter. 2. Bake chicken breast at 190°C for 18 minutes. 3. Serve with mushroom sauce and a sprig of thyme.",
                    "wine_logic": f"Madeira features high acidity ({acidity}/5) and a roasted nutty profile that complements mushroom dishes.",
                },
                {
                    "dish_type": "simple",
                    "title": "Aged Hard Cheese (Parmesan / Gruyère) with Olives & Walnuts",
                    "emoji": "",
                    "prep_time_min": 5,
                    "image_url": "/static/img/dishes/salmon_wine.jpg",
                    "short_why": "The savory saltiness of aged cheese and rich olives soften the warmth of Madeira and unlock vanilla notes.",
                    "recipe_brief": "1. Break aged Parmesan into rustic chunks. 2. Add a handful of walnuts and marinated olives. 3. Serve at room temperature.",
                    "wine_logic": "Crystalline aged cheese draws out hidden fruit and caramel nuances in Crimean Madeira.",
                },
            ],
            "unusual": [
                {
                    "dish_type": "unusual",
                    "title": "Rich French Onion Soup with Melted Gruyère Crouton",
                    "emoji": "",
                    "prep_time_min": 35,
                    "image_url": "/static/img/dishes/burger_wine.jpg",
                    "short_why": "Caramelized onions and melted Gruyère sing in harmony with the roasted nutty bouquet of Crimean Madeira.",
                    "recipe_brief": "1. Slowly caramelize onions in butter for 25 minutes. 2. Add beef broth and simmer for 10 minutes. 3. Top with a Gruyère baguette slice and broil until golden.",
                    "wine_logic": "Madeira is the classic partner for French onion soup, echoing the caramelized sugars of slow-cooked onions.",
                },
                {
                    "dish_type": "unusual",
                    "title": "Hot-Smoked Halibut or Eel with Fresh Lemon",
                    "emoji": "",
                    "prep_time_min": 5,
                    "image_url": "/static/img/dishes/salmon_wine.jpg",
                    "short_why": f"Powerful body ({body}/5) and smoky-cognac notes make Madeira the rare white wine capable of matching smoked fish.",
                    "recipe_brief": "1. Slice smoked halibut or eel into thin ribbons. 2. Drizzle with fresh lemon juice. 3. Serve with toasted dark rye bread.",
                    "wine_logic": "Smoky maderization tones harmonize with rich smoked fish without any metallic aftertaste.",
                },
            ],
        }
    if tannins >= 2.8:
        return {
            "simple": [
                {
                    "dish_type": "simple",
                    "title": "Juicy Homemade Beef Burger with Melted Cheddar",
                    "emoji": "",
                    "prep_time_min": 15,
                    "image_url": "/static/img/dishes/burger_wine.jpg",
                    "short_why": f"Tannins ({tannins}/5) bind with beef protein while acidity ({acidity}/5) cuts through rich melted Cheddar.",
                    "recipe_brief": "1. Form a ground beef patty and season with salt and pepper. 2. Grill for 3 min per side and melt a slice of Cheddar on top. 3. Serve on a toasted brioche bun with crisp greens.",
                    "wine_logic": f"Tannic red wine ({tannins}/5) calls for hot, juicy meat. Serve at 16–18°C in a Bordeaux glass.",
                },
                {
                    "dish_type": "simple",
                    "title": "Chargrilled Prime Ribeye Steak with Garlic-Herb Butter",
                    "emoji": "",
                    "prep_time_min": 15,
                    "image_url": "/static/img/dishes/steak_wine.jpg",
                    "short_why": f"Firm tannins ({tannins}/5) and body ({body}/5) tenderize marbled beef fibers and make dark berry aromas shine twice as bright.",
                    "recipe_brief": "1. Preheat a heavy cast-iron skillet or grill until smoking. 2. Sear the steak for 2.5 min per side to Medium Rare. 3. Top with thyme-garlic butter and rest for 5 minutes.",
                    "wine_logic": "Meat proteins soften high tannins, replacing astringency with a velvety berry bouquet.",
                },
            ],
            "unusual": [
                {
                    "dish_type": "unusual",
                    "title": "Marbled Beef Steak with Dark Berry & Rosemary Jus",
                    "emoji": "",
                    "prep_time_min": 20,
                    "image_url": "/static/img/dishes/steak_wine.jpg",
                    "short_why": f"Berry wine reduction and full body ({body}/5) create a deep velvety texture and highlight oak aging.",
                    "recipe_brief": "1. Sear the steak until golden-brown. 2. Reduce 50 ml of red wine with blackcurrants and rosemary. 3. Spoon the warm berry glaze over sliced steak.",
                    "wine_logic": "Oak-aged tannic reds shine brightest alongside a rich reduction sauce that bridges the barrel notes.",
                },
            ],
        }
    return {
        "simple": [
            {
                "dish_type": "simple",
                "title": "Wild Salmon Tartare with Ripe Avocado & Ponzu",
                "emoji": "",
                "prep_time_min": 12,
                "image_url": "/static/img/dishes/salmon_wine.jpg",
                "short_why": f"Crisp acidity ({acidity}/5) acts like a squeeze of fresh lemon: it highlights the sweetness of salmon and refreshes the palate.",
                "recipe_brief": "1. Dice fresh salmon fillet and ripe avocado into neat cubes. 2. Dress with lime juice, olive oil, and ponzu sauce. 3. Plate using a ring mold and garnish with microgreens.",
                "wine_logic": f"Light body ({body}/5) and vibrant acidity ({acidity}/5) never overwhelm delicate fish. Serve chilled at 8–10°C.",
            },
            {
                "dish_type": "simple",
                "title": "Pan-Seared Salmon or Sea Bass on Warm Spinach",
                "emoji": "",
                "prep_time_min": 15,
                "image_url": "/static/img/dishes/salmon_wine.jpg",
                "short_why": f"Acidity ({acidity}/5) cleanses the richness of fish oils, keeping the dinner fresh and light.",
                "recipe_brief": "1. Wilt spinach in a pan with butter and garlic for 1 minute. 2. Sear fish fillet skin-side down for 3–4 minutes until crispy. 3. Serve over spinach with a squeeze of lemon.",
                "wine_logic": "White and rosé wines with lively acidity act as a natural flavor enhancer for fish and seafood.",
            },
        ],
        "unusual": [
            {
                "dish_type": "unusual",
                "title": "White Fish Ceviche with Lime, Mango & Cilantro",
                "emoji": "",
                "prep_time_min": 15,
                "image_url": "/static/img/dishes/salmon_wine.jpg",
                "short_why": f"High wine acidity ({acidity}/5) matches the citrus marinade, making the wine taste lush and fruity by contrast.",
                "recipe_brief": "1. Slice white fish fillet thinly. 2. Marinate in fresh lime juice with red onion and cilantro for 7 minutes. 3. Fold in ripe mango cubes and serve chilled.",
                "wine_logic": "When wine acidity matches the lime marinade, floral and peach notes blossom on the finish.",
            },
        ],
    }


def translate_osm_stores_list_en(stores: List[Any]) -> List[Dict[str, Any]]:
    brand_map = {
        "Фирменный бутик Фанагория": "Fanagoria Signature Boutique",
        "Ателье вина Абрау-Дюрсо": "Abrau-Durso Wine Atelier",
        "Крымские вина Массандра": "Massandra Crimean Wines",
        "Сеть «Красное & Белое»": "Krasnoe & Beloe Wine & Spirits",
        "Сеть «ВинЛаб»": "Winelab Chain",
        "Винный маркет «Алкотека»": "Alkoteka Wine Market",
        "Винотека SimpleWine": "SimpleWine Boutique",
        "Сеть «Ароматный Мир»": "Aromatny Mir Wine Market",
        "Винный бутик & Энотека": "Wine Boutique & Enoteca",
        "Фирменный магазин «Вина Кубани»": "Kuban Wines Boutique",
        "Гастротека «Сыр и Вино»": "Cheese & Wine Gastroteca",
        "Винный магазин": "Wine Store",
    }
    out = []
    for s in stores:
        d = s.model_dump() if hasattr(s, "model_dump") else (s.dict() if hasattr(s, "dict") else dict(s))
        d["name"] = transliterate_ru_en(str(d.get("name", "Wine Store")))
        d["brand"] = brand_map.get(d.get("brand", ""), transliterate_ru_en(str(d.get("brand", "Wine Store"))))
        addr = str(d.get("address", ""))
        addr = (
            addr.replace("улица", "St.")
            .replace("ул.", "St.")
            .replace("проспект", "Ave.")
            .replace("пр-т", "Ave.")
            .replace("бульвар", "Blvd.")
            .replace("площадь", "Sq.")
            .replace("шоссе", "Hwy.")
            .replace("переулок", "Ln.")
            .replace("набережная", "Emb.")
            .replace("Адрес на карте", "Address on map")
        )
        d["address"] = transliterate_ru_en(addr)
        out.append(d)
    return out


def generate_sommelier_toast_v2_en(
    occasion: str,
    user_question: str = "",
    wine_name: str = "Selected Russian Wine",
    wine_slug: str = "",
    acidity: float = 4.0,
    tannins: float = 3.0,
) -> Dict[str, Any]:
    en_wine_name = translate_wine_name(wine_name, "en")
    hist = get_wine_history_record_en(wine_slug)
    historical_hook = ""
    if hist:
        historical_hook = (
            f"By the way, in our glasses is a true historical legend ({hist['wine_name']}, {hist['creation_year']}). "
            f"It was admired by {', '.join(hist['celebrities_badges'][:3])}!"
        )

    toasts_by_occasion = {
        "birthday": {
            "title": "Birthday Toast: «To Noble Aging and Southern Sunshine»",
            "toast_text": (
                f"Friends! A great person, just like a fine wine «{en_wine_name}», doesn't simply grow older "
                f"each year — they gain depth, a rare bouquet, and noble character. "
                f"{historical_hook} May your life hold as much warm southern sunshine as this vine absorbed, "
                f"may joy sparkle with lively acidity ({acidity}/5), and may your spirit remain just as harmonious. "
                f"To your finest vintage!"
            ),
        },
        "romance": {
            "title": "Toast for a Romantic Evening: «To the Chemistry of the Senses»",
            "toast_text": (
                f"They say the perfect culinary pairing is born when wine and food bring out the best in each other "
                f"and make the world fade away. In a glass of «{en_wine_name}», the passion of southern terroir meets "
                f"a tender, lingering finish. {historical_hook} Let's raise our glasses to our own synergy — "
                f"may every evening together leave a warm, unforgettable aftertaste!"
            ),
        },
        "friends": {
            "title": "Toast for Friends: «To Those Who Need No Occasion»",
            "toast_text": (
                f"Prince Lev Golitsyn once said that wine is sunlight captured in glass that truly comes alive "
                f"only among true friends. Tonight we share «{en_wine_name}». {historical_hook} "
                f"Here's to making our gatherings as warm, sincere, and inspiring as the southern bouquet in our glasses!"
            ),
        },
        "victory": {
            "title": "Toast to Success & Triumph: «Diplomacy of Winners»",
            "toast_text": (
                f"In February 1945 at Livadia Palace, historic decisions were celebrated over a glass of Crimean wine. "
                f"Today we celebrate our own milestone and our own victory! In our glasses is «{en_wine_name}». "
                f"{historical_hook} To bold ideas, decisive action, and the triumph of every endeavor!"
            ),
        },
    }

    chosen = toasts_by_occasion.get(occasion, toasts_by_occasion["friends"])
    sommelier_tip = (
        f"**Sommelier Serving Tip for «{en_wine_name}»:** "
        f"Notice the balance of acidity ({acidity}/5) and tannins ({tannins}/5). "
        f"Fill the glass no more than one-third full so the aromatic esters concentrate near the rim."
    )
    if user_question:
        sommelier_tip += (
            f"\n\n**Answer to your question («{user_question}»):** "
            f"Wines with this sensory profile from our catalog are an ideal match for your request — "
            f"you can view them on the Wine Map and walk to the nearest wine boutique."
        )

    return {
        "toast_title": chosen["title"],
        "toast_text": chosen["toast_text"],
        "sommelier_advice": sommelier_tip,
        "has_history": hist is not None,
    }


# ---------------------------------------------------------------------------
# 10. DIALOG & PAIRING ROUTER HELPERS (/api/sommelier/*)
# ---------------------------------------------------------------------------

def _translate_fact_line_en(fact_str: str) -> str:
    if not fact_str:
        return ""
    s = str(fact_str)
    for ru_r, en_r in sorted(REGION_MAP_RU_EN.items(), key=lambda x: -len(x[0])):
        s = re.sub(re.escape(ru_r), en_r, s, flags=re.IGNORECASE)
    for ru_g, en_g in sorted(GRAPE_MAP_RU_EN.items(), key=lambda x: -len(x[0])):
        s = re.sub(r"(?<![а-яА-ЯёЁ])" + re.escape(ru_g) + r"(?![а-яА-ЯёЁ])", en_g.strip(), s, flags=re.IGNORECASE)
    replacements = [
        ("Красное", "Red"), ("красное", "red"),
        ("Белое", "White"), ("белое", "white"),
        ("Розовое", "Rosé"), ("розовое", "rosé"),
        ("Оранжевое", "Orange"), ("оранжевое", "orange"),
        ("игристое", "sparkling"), ("Игристое", "Sparkling"),
        ("полусухое", "off-dry"), ("полусладкое", "semi-sweet"),
        ("сухое", "dry"), ("сладкое", "sweet"), ("брют", "brut"),
        ("тело лёгкое", "light body"), ("тело среднее", "medium body"), ("тело плотное", "full body"),
        ("кислотность мягкая", "soft acidity"), ("кислотность умеренная", "balanced acidity"), ("кислотность живая, яркая", "crisp, lively acidity"),
        ("танины мягкие", "soft tannins"), ("танины умеренные", "moderate tannins"), ("танины выраженные", "firm tannins"),
        ("выдержка в дубе", "oak aged"), ("подача", "serve at"), ("алк.", "alc."), ("мес.", "mo."),
    ]
    for rk, ev in replacements:
        s = s.replace(rk, ev)
    if re.search(r"[а-яА-ЯёЁ]", s):
        s = transliterate_ru_en(s)
    return s


def translate_dialog_ask_response_en(result: Dict[str, Any], query: str = "") -> Dict[str, Any]:
    out = copy.deepcopy(result)
    picks = out.get("picks", [])
    en_picks = []
    for p in picks:
        p_copy = dict(p)
        p_copy["name"] = translate_wine_name(p.get("name"), "en")
        p_copy["winery"] = translate_winery(p.get("winery"), "en")
        p_copy["region"] = translate_region(p.get("region"), "en")
        p_copy["category"] = translate_category(p.get("category"), "en")
        p_copy["grapes"] = [translate_grape(g, "en") for g in (p.get("grapes") or [])]
        p_copy["facts"] = _translate_fact_line_en(p.get("facts", ""))
        p_copy["reasons"] = [
            f"Selected for its harmonious balance, varietal character, and food-pairing versatility."
        ]
        en_picks.append(p_copy)
    out["picks"] = en_picks

    kind = out.get("kind", "")
    if en_picks:
        lines = ["Here are the top wines from our catalog tailored to your request:"]
        for i, ep in enumerate(en_picks, 1):
            lines.append(f"{i}. «{ep['name']}» ({ep['winery']}) — {ep['facts']}")
        lines.append("\nInformation is for reference only. Excessive alcohol consumption is harmful to your health (18+).")
        out["text"] = "\n".join(lines)
    elif kind == "clarify":
        out["text"] = (
            "Please tell me a bit more about what you're looking for — for example, the dish you're serving "
            "(steak, fish, pasta, cheese), or your preferred wine style (dry red, crisp white, rosé, sparkling)."
        )
    elif kind == "offtopic" or kind == "guardrail":
        out["text"] = "I am your AI Wine Sommelier and can help you choose wines, food pairings, tasting notes, and toasts."
    else:
        out["text"] = translate_wine_description(out.get("text", ""), None, "en")

    out["note"] = "Reference information based on catalog descriptions (18+)."
    return out


def translate_dialog_wine_info_en(result: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(result)
    card = out.get("card") or {}
    en_card = translate_wine_dict_en(card) if card else {}
    out["card"] = en_card
    if out.get("profile"):
        out["profile"] = translate_sommelier_profile_en(out["profile"], card)
    food_map = {
        "сыр": "Cheeses",
        "красное мясо": "Red meat & steaks",
        "птица": "Poultry",
        "свинина": "Pork & charcuterie",
        "рыба": "Fish",
        "морепродукты": "Seafood",
        "десерт": "Desserts",
        "закуски": "Appetizers",
        "паста/пицца": "Pasta & risotto",
        "овощи/салат": "Salads & vegetables",
        "острое/азиатская": "Spicy & Asian cuisine",
        "аперитив": "Aperitif",
    }
    out["best_dishes"] = [food_map.get(d, d) for d in out.get("best_dishes", [])]
    if en_card:
        out["text"] = (
            f"«{en_card.get('name')}» ({en_card.get('winery')}, {en_card.get('region')}). "
            f"Grape: {en_card.get('grape')}. {en_card.get('description')}"
        )
    out["note"] = "Reference information based on catalog descriptions (18+)."
    return out


def translate_dialog_alternatives_en(result: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(result)
    en_items = []
    for it in out.get("items", []):
        it_c = dict(it)
        it_c["name"] = translate_wine_name(it.get("name"), "en")
        it_c["winery"] = translate_winery(it.get("winery"), "en")
        it_c["facts"] = _translate_fact_line_en(it.get("facts", ""))
        it_c["reasons"] = ["Similar sensory style, grape profile, and regional character"]
        en_items.append(it_c)
    out["items"] = en_items
    return out


DISH_QUERY_EN_TO_RU: Dict[str, str] = {
    "steak": "стейк",
    "beef": "говядина",
    "ribeye": "стейк рибай",
    "meat": "мясо",
    "bbq": "шашлык",
    "kebab": "шашлык",
    "lamb": "баранина",
    "burger": "бургер",
    "pork": "свинина",
    "duck": "утка",
    "chicken": "курица",
    "poultry": "птица",
    "turkey": "индейка",
    "fish": "рыба",
    "salmon": "лосось",
    "trout": "форель",
    "seafood": "морепродукты",
    "shrimp": "креветки",
    "prawns": "креветки",
    "oysters": "устрицы",
    "mussels": "мидии",
    "scallops": "гребешки",
    "pasta": "паста",
    "risotto": "ризотто",
    "pizza": "пицца",
    "cheese": "сыр",
    "cheeses": "сырная тарелка",
    "salad": "салат",
    "vegetables": "овощи",
    "mushrooms": "грибы",
    "dessert": "десерт",
    "chocolate": "шоколад",
    "fruit": "фрукты",
    "fruits": "фрукты",
    "sushi": "суши",
    "rolls": "роллы",
    "tom yum": "том ям",
}


def map_en_dish_query_to_ru(query: str) -> str:
    if not query:
        return query
    q_low = query.strip().lower()
    if q_low in DISH_QUERY_EN_TO_RU:
        return DISH_QUERY_EN_TO_RU[q_low]
    res = query
    for en_w, ru_w in sorted(DISH_QUERY_EN_TO_RU.items(), key=lambda x: -len(x[0])):
        if en_w in q_low:
            return ru_w
    return res


def translate_pairing_response_en(resp: Dict[str, Any]) -> Dict[str, Any]:
    if not resp:
        return resp
    out = copy.deepcopy(resp)
    role_map = {
        "Лучшее сочетание": "Best Pairing Match",
        "Российская классика": "Russian Classic",
        "Другой сорт": "Alternative Grape",
        "Выгодный выбор": "Smart Value",
    }
    en_wines = []
    for w in out.get("wines", []):
        wc = dict(w)
        wc["name"] = translate_wine_name(w.get("name"), "en")
        wc["producer"] = translate_winery(w.get("producer"), "en")
        wc["region"] = translate_region(w.get("region"), "en")
        wc["country"] = "Russia"
        wc["grape"] = translate_grape(w.get("grape"), "en")
        wc["color"] = translate_color(w.get("color"), "en")
        wc["sweetness"] = translate_sugar(w.get("sweetness"), "en").lower()
        wc["role_label"] = role_map.get(w.get("role_label", ""), "Recommended")
        wc["story"] = f"{wc['grape']} grown in {wc['region']}: expressive varietal character with balanced structure."
        wc["explanation"] = f"{wc['name']} ({wc['producer']}): body, acidity, and tannin profile harmonize with the dish's texture."
        en_wines.append(wc)
    out["wines"] = en_wines

    en_grapes = []
    for g in out.get("grapes", []):
        gc = dict(g)
        gc["name"] = translate_grape(g.get("name"), "en")
        gc["rule"] = "Balanced acidity and structure complement the dish's flavor profile."
        gc["story"] = f"{gc['name']} — expressive grape variety well suited for this gastronomic pairing."
        en_grapes.append(gc)
    out["grapes"] = en_grapes

    if en_wines:
        summary_parts = [f"{w['name']} ({w['producer']}, {w['grape']}, {int(w.get('price_rub') or 990)} ₽)" for w in en_wines]
        out["explanation"] = "Recommended wines for your dish: " + "; ".join(summary_parts) + "."
    elif out.get("kind") == "clarify":
        out["explanation"] = "Please specify the main ingredient or dish (e.g., steak, salmon, pasta, cheese, seafood, dessert)."

    out["note"] = "Reference pairing based on wine and food sensory profiles (18+)."
    return out
