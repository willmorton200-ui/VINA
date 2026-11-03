# -*- coding: utf-8 -*-
"""
VINA World Analogs Engine (Нероссийские аналоги)
================================================
Provides bidirectional matching:
1. Russian Wine -> Up to 3 World / Foreign Benchmark Analogs (with similarity %, rationale, country flag)
2. Foreign Wine Query -> Up to 3 Best Russian Twin Wines from the 2,108 catalog registry.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------------------------------------------------------
# 1. Расширенный справочник мировых эталонов (World Wine Benchmarks)
# -----------------------------------------------------------------------------

WORLD_BENCHMARKS = [
    # ========================== БЕЛЫЕ ВИНА ==========================
    {
        "id": "chablis-premier-cru",
        "name_ru": "Шабли Премье Крю",
        "name_en": "Chablis Premier Cru AOC",
        "appellation_ru": "Франция, Бургундия (Шабли)",
        "appellation_en": "France, Burgundy (Chablis)",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Шардоне",
        "grape_en": "100% Chardonnay",
        "grapes_keys": ["chardonnay", "шардоне"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.8,
        "acidity": 4.5,
        "tannins": 0.0,
        "tags": ["шабли", "chablis", "киммеридж", "минеральное", "чистое шардоне"],
        "rationale_ru": "Хрустящая известняковая кислотность, ноты зеленого яблока, кремня и белых цветов без маслянистости дуба.",
        "rationale_en": "Crisp Kimmeridgian limestone acidity, green apple, flint, and white blossoms without buttery oak."
    },
    {
        "id": "meursault-burgundy",
        "name_ru": "Мерсо / Пюлиньи-Монраше",
        "name_en": "Meursault / Puligny-Montrachet AOC",
        "appellation_ru": "Франция, Бургундия (Кот-де-Бон)",
        "appellation_en": "France, Burgundy (Côte de Beaune)",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Шардоне (выдержка в дубе)",
        "grape_en": "100% Chardonnay (Oak Aged)",
        "grapes_keys": ["chardonnay", "шардоне"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 3.8,
        "acidity": 3.8,
        "tannins": 0.2,
        "tags": ["мерсо", "meursault", "монраше", "montrachet", "белая бургундия", "шардоне бочка"],
        "rationale_ru": "Сливочно-кремовая плотность, тона теплой бриоши, сливочного масла, спелого персика и благородного дуба.",
        "rationale_en": "Creamy buttery palate weight, warm brioche, ripe white peach, and fine French oak vanilla integration."
    },
    {
        "id": "sancerre-loire",
        "name_ru": "Сансер / Пуйи-Фюме",
        "name_en": "Sancerre / Pouilly-Fumé AOC",
        "appellation_ru": "Франция, Долина Луары",
        "appellation_en": "France, Loire Valley",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Совиньон Блан",
        "grape_en": "100% Sauvignon Blanc",
        "grapes_keys": ["sauvignon", "совиньон"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.5,
        "acidity": 4.5,
        "tannins": 0.0,
        "tags": ["сансер", "sancerre", "пуйи-фюме", "pouilly-fume", "луара", "совиньон блан", "sauvignon blanc"],
        "rationale_ru": "Кремнистая минеральность, лист черной смородины, крыжовник, мокрый камень и звонкая свежесть.",
        "rationale_en": "Flinty minerality, crushed blackcurrant leaf, gooseberry, wet stone, and vibrant electric tension."
    },
    {
        "id": "marlborough-sauvignon",
        "name_ru": "Совиньон Блан Мальборо",
        "name_en": "Marlborough Sauvignon Blanc",
        "appellation_ru": "Новая Зеландия, Мальборо",
        "appellation_en": "New Zealand, Marlborough",
        "flag": "🇳🇿",
        "country_ru": "Новая Зеландия",
        "country_en": "New Zealand",
        "grape_ru": "100% Совиньон Блан",
        "grape_en": "100% Sauvignon Blanc",
        "grapes_keys": ["sauvignon", "совиньон"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.8,
        "acidity": 4.6,
        "tannins": 0.0,
        "tags": ["мальборо", "marlborough", "совиньон блан", "sauvignon blanc", "новая зеландия", "new zealand"],
        "rationale_ru": "Взрывная палитра маракуйи, грейпфрута, лайма, свежескошенной травы и сочной бодрящей кислотности.",
        "rationale_en": "Explosive passionfruit, pink grapefruit, lime zest, cut grass, and mouthwatering crisp finish."
    },
    {
        "id": "mosel-riesling",
        "name_ru": "Рислинг Мозеля",
        "name_en": "Mosel Riesling Dry / Off-Dry",
        "appellation_ru": "Германия, Мозель",
        "appellation_en": "Germany, Mosel",
        "flag": "🇩🇪",
        "country_ru": "Германия",
        "country_en": "Germany",
        "grape_ru": "100% Рислинг",
        "grape_en": "100% Riesling",
        "grapes_keys": ["riesling", "рислинг"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.2,
        "acidity": 4.8,
        "tannins": 0.0,
        "tags": ["рислинг", "riesling", "мозель", "mosel", "германия"],
        "rationale_ru": "Сланцевая стальная минеральность, зеленое яблоко, сочный белый персик и филигранный баланс кислотности.",
        "rationale_en": "Slate minerality, green apple, juicy white peach, and filigree acid-fruit balance."
    },
    {
        "id": "alsace-riesling",
        "name_ru": "Рислинг Эльзаса Гран Крю",
        "name_en": "Alsace Grand Cru Riesling",
        "appellation_ru": "Франция, Эльзас",
        "appellation_en": "France, Alsace",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Рислинг",
        "grape_en": "100% Riesling",
        "grapes_keys": ["riesling", "рислинг"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 3.4,
        "acidity": 4.5,
        "tannins": 0.0,
        "tags": ["эльзас", "alsace", "рислинг эльзас", "сухой рислинг"],
        "rationale_ru": "Сухой плотный гастрономичный стиль: спелые цитрусы, бензольные благородные нюансы и долгое минеральное послевкусие.",
        "rationale_en": "Bone-dry structured style: ripe citrus, noble petrol notes, and prolonged stony finish."
    },
    {
        "id": "gavi-piemonte",
        "name_ru": "Гави ди Гави",
        "name_en": "Gavi di Gavi DOCG",
        "appellation_ru": "Италия, Пьемонт",
        "appellation_en": "Italy, Piedmont",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "100% Кортезе",
        "grape_en": "100% Cortese",
        "grapes_keys": ["cortese", "кортезе", "кокур", "алиготе"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.5,
        "acidity": 4.0,
        "tannins": 0.0,
        "tags": ["гави", "gavi", "cortese", "кортезе", "итальянское белое"],
        "rationale_ru": "Изысканная миндальная горчинка, белый персик, ромашка и деликатная свежесть пьемонтских холмов.",
        "rationale_en": "Delicate almond bitterness, crisp white peach, chamomile, and Piedmontese hill freshness."
    },
    {
        "id": "pinot-grigio-friuli",
        "name_ru": "Пино Гриджо Фриули",
        "name_en": "Friuli Pinot Grigio DOC",
        "appellation_ru": "Италия, Фриули-Венеция-Джулия",
        "appellation_en": "Italy, Friuli-Venezia Giulia",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "100% Пино Гриджо",
        "grape_en": "100% Pinot Grigio",
        "grapes_keys": ["pinot grigio", "пино гриджо", "пино гри", "pinot gris"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.6,
        "acidity": 3.8,
        "tannins": 0.0,
        "tags": ["пино гриджо", "pinot grigio", "пино гри", "pinot gris", "фриули"],
        "rationale_ru": "Тонкие оттенки спелой груши дюшес, желтого яблока, цитрусовой цедры и мягкая освежающая минеральность.",
        "rationale_en": "Subtle Bartlett pear, golden apple, lemon peel, and clean refreshing alpine minerality."
    },
    {
        "id": "albarino-rias-baixas",
        "name_ru": "Альбариньо Риас Байшас",
        "name_en": "Rías Baixas Albariño DO",
        "appellation_ru": "Испания, Галисия",
        "appellation_en": "Spain, Galicia",
        "flag": "🇪🇸",
        "country_ru": "Испания",
        "country_en": "Spain",
        "grape_ru": "100% Альбариньо",
        "grape_en": "100% Albariño",
        "grapes_keys": ["albarino", "альбариньо"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 3.0,
        "acidity": 4.5,
        "tannins": 0.0,
        "tags": ["альбариньо", "albarino", "риас байшас", "испанское белое"],
        "rationale_ru": "Морской бриз, солоноватая атлантическая свежесть, белый персик, абрикос и яркая гастрономичная кислотность.",
        "rationale_en": "Atlantic saline breeze, sea salt minerality, white peach, apricot, and crisp gastronomic acidity."
    },
    {
        "id": "gruner-veltliner-wachau",
        "name_ru": "Грюнер Вельтлинер Вахау",
        "name_en": "Wachau Grüner Veltliner Smaragd",
        "appellation_ru": "Австрия, Вахау",
        "appellation_en": "Austria, Wachau",
        "flag": "🇦🇹",
        "country_ru": "Австрия",
        "country_en": "Austria",
        "grape_ru": "100% Грюнер Вельтлинер",
        "grape_en": "100% Grüner Veltliner",
        "grapes_keys": ["gruner", "грюнер", "вельтлинер"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 3.2,
        "acidity": 4.2,
        "tannins": 0.0,
        "tags": ["грюнер", "gruner", "veltliner", "австрия", "вахау"],
        "rationale_ru": "Знаменитый тон белого перца, сочного зеленого яблока, чечевицы и мощная минеральная основа Дуная.",
        "rationale_en": "Signature white pepper spice, crunchy green apple, lentil notes, and dense stony Danube minerality."
    },
    {
        "id": "gewurztraminer-alsace",
        "name_ru": "Гевюрцтраминер Эльзаса",
        "name_en": "Alsace Gewürztraminer AOC",
        "appellation_ru": "Франция, Эльзас",
        "appellation_en": "France, Alsace",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Гевюрцтраминер",
        "grape_en": "100% Gewürztraminer",
        "grapes_keys": ["gewurz", "гевюрц", "траминер"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 1,
        "oak": False,
        "body": 3.8,
        "acidity": 3.0,
        "tannins": 0.1,
        "tags": ["гевюрц", "gewurztraminer", "траминер", "ароматное"],
        "rationale_ru": "Пышный экзотический аромат лепестков чайной розы, личи, восточных пряностей и спелого манго.",
        "rationale_en": "Opulent exotic bouquet of tea rose petals, lychee, oriental spices, and ripe mango."
    },
    {
        "id": "viognier-condrieu",
        "name_ru": "Вионье Кондриё",
        "name_en": "Condrieu Viognier AOC",
        "appellation_ru": "Франция, Северная Рона",
        "appellation_en": "France, Northern Rhône",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Вионье",
        "grape_en": "100% Viognier",
        "grapes_keys": ["viognier", "вионье"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 3.7,
        "acidity": 3.2,
        "tannins": 0.1,
        "tags": ["вионье", "viognier", "кондриё", "condrieu"],
        "rationale_ru": "Шелковистое маслянистое тело, аромат белого персика, абрикосового джема, флердоранжа и мускуса.",
        "rationale_en": "Silky oily texture, lush white peach, apricot confit, orange blossom, and delicate musk."
    },
    {
        "id": "napa-chardonnay",
        "name_ru": "Шардоне Долины Напа",
        "name_en": "Napa Valley Oak Chardonnay",
        "appellation_ru": "США, Калифорния (Напа)",
        "appellation_en": "USA, California (Napa Valley)",
        "flag": "🇺🇸",
        "country_ru": "США",
        "country_en": "USA",
        "grape_ru": "100% Шардоне (бочковая выдержка)",
        "grape_en": "100% Chardonnay (Oak Barrel Aged)",
        "grapes_keys": ["chardonnay", "шардоне"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.0,
        "acidity": 3.5,
        "tannins": 0.2,
        "tags": ["напа", "napa", "калифорния", "california", "дубовое шардоне"],
        "rationale_ru": "Насыщенный калифорнийский стиль: печеное яблоко, ванильный крем, жареный фундук и карамельное масло.",
        "rationale_en": "Lush Californian style: baked apple, vanilla crème brûlée, toasted hazelnut, and melted butter."
    },

    # ========================== КРАСНЫЕ ВИНА ==========================
    {
        "id": "bordeaux-medoc",
        "name_ru": "Бордо Гран Крю (Медок / Пойяк)",
        "name_en": "Bordeaux Médoc / Pauillac Grand Cru",
        "appellation_ru": "Франция, Бордо (Левый берег)",
        "appellation_en": "France, Bordeaux (Left Bank)",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Каберне Совиньон, Мерло",
        "grape_en": "Cabernet Sauvignon, Merlot",
        "grapes_keys": ["cabernet", "каберне", "merlot", "мерло"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.5,
        "acidity": 3.8,
        "tannins": 4.6,
        "tags": ["бордо", "bordeaux", "медок", "medoc", "пойяк", "pauillac", "грав", "каберне"],
        "rationale_ru": "Классическая бордоская структура: черная смородина, кедр, сигарный хьюмидор, графит и мощные благородные танины.",
        "rationale_en": "Classic Left Bank architecture: cassis, cedar box, cigar humidor, graphite pencil lead, and firm noble tannins."
    },
    {
        "id": "saint-emilion-merlot",
        "name_ru": "Сент-Эмильон Гран Крю (Мерло)",
        "name_en": "Saint-Émilion Grand Cru (Merlot)",
        "appellation_ru": "Франция, Бордо (Правый берег)",
        "appellation_en": "France, Bordeaux (Right Bank)",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Мерло, Каберне Фран",
        "grape_en": "Merlot, Cabernet Franc",
        "grapes_keys": ["merlot", "мерло"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.0,
        "acidity": 3.6,
        "tannins": 3.8,
        "tags": ["сент-эмильон", "saint-emilion", "помероль", "pomerol", "мерло", "merlot"],
        "rationale_ru": "Бархатные округлые танины, спелая черная слива, темный шоколад, вишня в ликере и мягкое теплое послевкусие.",
        "rationale_en": "Velvety rounded tannins, ripe dark plum, bitter chocolate, liqueur cherry, and opulent pliant finish."
    },
    {
        "id": "bourgogne-pinot-noir",
        "name_ru": "Красная Бургундия (Пино Нуар)",
        "name_en": "Bourgogne Pinot Noir AOC",
        "appellation_ru": "Франция, Бургундия (Кот-де-Нюи)",
        "appellation_en": "France, Burgundy (Côte de Nuits)",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Пино Нуар",
        "grape_en": "100% Pinot Noir",
        "grapes_keys": ["pinot noir", "пино нуар", "цимлянский"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 2.8,
        "acidity": 4.5,
        "tannins": 2.6,
        "tags": ["бургундия", "burgundy", "пино нуар", "pinot noir", "кот-де-нюи"],
        "rationale_ru": "Шелковистые танины, лесная земляника, спелая вишня, подлесок, осенний лист и утонченная ягодная кислотность.",
        "rationale_en": "Silky transparent tannins, wild strawberry, red cherry, forest floor sous-bois, and energetic berry acidity."
    },
    {
        "id": "chianti-classico",
        "name_ru": "Кьянти Классико",
        "name_en": "Chianti Classico DOCG",
        "appellation_ru": "Италия, Тоскана",
        "appellation_en": "Italy, Tuscany",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "Санджовезе, Колорино",
        "grape_en": "Sangiovese, Colorino",
        "grapes_keys": ["sangiovese", "санджовезе", "кьянти"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 3.4,
        "acidity": 4.5,
        "tannins": 4.0,
        "tags": ["кьянти", "chianti", "тоскана", "tuscany", "санджовезе", "sangiovese"],
        "rationale_ru": "Сочная кислая вишня, сухие тосканские травы, бальзамик, табак и цепкие гастрономичные танины.",
        "rationale_en": "Sour Morello cherry, dried Tuscan oregano, balsamic glaze, pipe tobacco, and firm gastronomic tannins."
    },
    {
        "id": "brunello-di-montalcino",
        "name_ru": "Брунелло ди Монтальчино",
        "name_en": "Brunello di Montalcino DOCG",
        "appellation_ru": "Италия, Тоскана (Монтальчино)",
        "appellation_en": "Italy, Tuscany (Montalcino)",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "100% Санджовезе Гроссо",
        "grape_en": "100% Sangiovese Grosso",
        "grapes_keys": ["sangiovese", "санджовезе", "брунелло"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.4,
        "acidity": 4.4,
        "tannins": 4.6,
        "tags": ["брунелло", "brunello", "монтальчино", "montalcino"],
        "rationale_ru": "Монументальная глубина: вяленая вишня, кожаное седло, черный трюфель, пряности и многолетняя дубовая выдержка.",
        "rationale_en": "Monumental depth: dried red cherry, leather saddle, black truffle, sweet spices, and extended oak aging."
    },
    {
        "id": "barolo-piedmont",
        "name_ru": "Бароло (Король вин)",
        "name_en": "Barolo DOCG (The King of Wines)",
        "appellation_ru": "Италия, Пьемонт (Ланге)",
        "appellation_en": "Italy, Piedmont (Langhe)",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "100% Неббиоло",
        "grape_en": "100% Nebbiolo",
        "grapes_keys": ["nebbiolo", "неббиоло", "красностоп", "бароло"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.6,
        "acidity": 4.6,
        "tannins": 4.9,
        "tags": ["бароло", "barolo", "неббиоло", "nebbiolo", "пьемонт", "барбареско"],
        "rationale_ru": "Знаменитый дуэт смолы и роз (tar and roses), сушеная клюква, кожа, трюфель и мощный танинный скелет.",
        "rationale_en": "Legendary 'tar and roses' perfume, dried cranberry, worn leather, white truffle, and commanding tannin grip."
    },
    {
        "id": "amarone-valpolicella",
        "name_ru": "Амароне делла Вальполичелла",
        "name_en": "Amarone della Valpolicella DOCG",
        "appellation_ru": "Италия, Венето",
        "appellation_en": "Italy, Veneto",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "Корвина, Рондинелла (Аппассименто)",
        "grape_en": "Corvina, Rondinella (Appassimento)",
        "grapes_keys": ["corvina", "корвина", "амароне", "аппассименто"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 1,
        "oak": True,
        "body": 4.8,
        "acidity": 3.8,
        "tannins": 4.2,
        "tags": ["амароне", "amarone", "вальполичелла", "вяленый виноград"],
        "rationale_ru": "Богатейшая концентрация подвяленного винограда: вяленая вишня, инжир, горький шоколад, корица и бархат.",
        "rationale_en": "Rich appassimento concentration: dried sour cherries, figs, bitter chocolate, cinnamon, and warm velvety depth."
    },
    {
        "id": "rioja-gran-reserva",
        "name_ru": "Риоха Гран Резерва",
        "name_en": "Rioja Gran Reserva DOCa",
        "appellation_ru": "Испания, Риоха",
        "appellation_en": "Spain, Rioja",
        "flag": "🇪🇸",
        "country_ru": "Испания",
        "country_en": "Spain",
        "grape_ru": "Темпранильо, Грасиано",
        "grape_en": "Tempranillo, Graciano",
        "grapes_keys": ["tempranillo", "темпранильо", "риоха"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 3.8,
        "acidity": 4.0,
        "tannins": 3.6,
        "tags": ["риоха", "rioja", "темпранильо", "tempranillo", "испания"],
        "rationale_ru": "Долгая выдержка в дубе: ваниль, кокос, укропные пряности, сушеная клубника, табак и округлый бархат.",
        "rationale_en": "Extended American oak maturation: dill spice, vanilla pod, coconut, dried strawberry, tobacco leaf, and melted tannins."
    },
    {
        "id": "ribera-del-duero",
        "name_ru": "Рибера дель Дуэро (Тинто Фино)",
        "name_en": "Ribera del Duero DO",
        "appellation_ru": "Испания, Кастилия и Леон",
        "appellation_en": "Spain, Castilla y León",
        "flag": "🇪🇸",
        "country_ru": "Испания",
        "country_en": "Spain",
        "grape_ru": "100% Тинто Фино (Темпранильо)",
        "grape_en": "100% Tinto Fino (Tempranillo)",
        "grapes_keys": ["tempranillo", "темпранильо", "тинто фино"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.6,
        "acidity": 3.8,
        "tannins": 4.5,
        "tags": ["рибера", "ribera", "дуэро", "duero", "тинто фино"],
        "rationale_ru": "Мощный высокогорный темпранильо: спелая ежевика, черная вишня, дым костра, графит и плотные танины.",
        "rationale_en": "Powerhouse high-altitude Tempranillo: crushed blackberries, black cherry, woodsmoke, graphite, and muscular frame."
    },
    {
        "id": "mendoza-malbec",
        "name_ru": "Мальбек Мендосы",
        "name_en": "Mendoza Malbec (High Altitude)",
        "appellation_ru": "Аргентина, Мендоса",
        "appellation_en": "Argentina, Mendoza",
        "flag": "🇦🇷",
        "country_ru": "Аргентина",
        "country_en": "Argentina",
        "grape_ru": "100% Мальбек",
        "grape_en": "100% Malbec",
        "grapes_keys": ["malbec", "мальбек"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.4,
        "acidity": 3.4,
        "tannins": 3.8,
        "tags": ["мальбек", "malbec", "мендоса", "mendoza", "аргентина"],
        "rationale_ru": "Глубокий чернильный цвет, сочная спелая черника, слива, фиалка, сладкие танины и оттенки молочного шоколада.",
        "rationale_en": "Deep inky violet hue, crushed blueberries, dark plum, violet florals, pliant sweet tannins, and cocoa finish."
    },
    {
        "id": "syrah-rhone",
        "name_ru": "Сира Северной Роны (Кроз-Эрмитаж)",
        "name_en": "Northern Rhône Syrah (Crozes-Hermitage)",
        "appellation_ru": "Франция, Долина Роны",
        "appellation_en": "France, Rhône Valley",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Сира (Шираз)",
        "grape_en": "100% Syrah",
        "grapes_keys": ["syrah", "сира", "shiraz", "шираз"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.2,
        "acidity": 4.0,
        "tannins": 4.2,
        "tags": ["сира", "syrah", "шираз", "shiraz", "эрмитаж", "hermitage", "рона"],
        "rationale_ru": "Дробленый черный перец, копчености, маслины таджасские, темная вишня и породистая гранитная свежесть.",
        "rationale_en": "Freshly cracked black peppercorn, smoked charcuterie, black olive tapenade, and mineral-driven dark plum."
    },
    {
        "id": "barossa-shiraz",
        "name_ru": "Баросса Вэлли Шираз",
        "name_en": "Barossa Valley Old Vine Shiraz",
        "appellation_ru": "Австралия, Долина Баросса",
        "appellation_en": "Australia, Barossa Valley",
        "flag": "🇦🇺",
        "country_ru": "Австралия",
        "country_en": "Australia",
        "grape_ru": "100% Шираз (Сира)",
        "grape_en": "100% Shiraz",
        "grapes_keys": ["shiraz", "шираз", "syrah", "сира"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.9,
        "acidity": 3.2,
        "tannins": 4.2,
        "tags": ["баросса", "barossa", "шираз", "shiraz", "австралия"],
        "rationale_ru": "Колоссальная мощь: ежевичный джем, эвкалипт, шоколад, лакрица и сладкие пышные танины старых лоз.",
        "rationale_en": "Huge fruit concentration: blackberry jam, eucalyptus mint, dark chocolate, liquorice, and old-vine richness."
    },
    {
        "id": "chateauneuf-du-pape",
        "name_ru": "Шатонёф-дю-Пап",
        "name_en": "Châteauneuf-du-Pape AOC",
        "appellation_ru": "Франция, Южная Рона",
        "appellation_en": "France, Southern Rhône",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Гренаш, Сира, Мурведр",
        "grape_en": "Grenache, Syrah, Mourvèdre",
        "grapes_keys": ["grenache", "гренаш", "гарнача", "mourvedre", "мурведр"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.5,
        "acidity": 3.6,
        "tannins": 4.2,
        "tags": ["шатонёф", "chateauneuf", "гренаш", "gsm"],
        "rationale_ru": "Согревающий южный характер: спелая малина, прованские травы (гарриг), пряный белый перец и бархатная текстура.",
        "rationale_en": "Generous warm palate: Kirsch liqueur, wild garrigue herbs, white pepper, lavender, and full-bodied velvet."
    },
    {
        "id": "primitivo-zinfandel",
        "name_ru": "Примитиво ди Мандурия",
        "name_en": "Primitivo di Manduria / Zinfandel",
        "appellation_ru": "Италия, Апулия",
        "appellation_en": "Italy, Puglia",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "100% Примитиво (Зинфандель)",
        "grape_en": "100% Primitivo (Zinfandel)",
        "grapes_keys": ["primitivo", "примитиво", "zinfandel", "зинфандель"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 1,
        "oak": True,
        "body": 4.7,
        "acidity": 3.2,
        "tannins": 3.6,
        "tags": ["примитиво", "primitivo", "зинфандель", "zinfandel", "мандурия"],
        "rationale_ru": "Спелая вяленая вишня, ежевика, чернослив, корица, ваниль и мягкая обволакивающая ягодная сладость.",
        "rationale_en": "Sun-drenched dark berry jam, prune, cinnamon bark, vanilla, and sweet-fruited enveloping finish."
    },
    {
        "id": "madiran-tannat",
        "name_ru": "Мадиран (Таннат)",
        "name_en": "Madiran AOC (Tannat)",
        "appellation_ru": "Франция, Юго-Запад",
        "appellation_en": "France, South West",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "100% Таннат",
        "grape_en": "100% Tannat",
        "grapes_keys": ["tannat", "таннат", "красностоп"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.8,
        "acidity": 4.4,
        "tannins": 5.0,
        "tags": ["мадиран", "madiran", "таннат", "tannat", "красностоп"],
        "rationale_ru": "Экстремальная танинная мощь, дикая черная смородина, терн, кожа и монументальный потенциал к мясу на гриле.",
        "rationale_en": "Monolithic tannin architecture, blackthorn, wild cassis, saddle leather, and supreme synergy with grilled red steak."
    },
    {
        "id": "georgia-saperavi",
        "name_ru": "Грузинское Саперави (Мукузани)",
        "name_en": "Georgian Saperavi (Mukuzani)",
        "appellation_ru": "Грузия, Кахетия",
        "appellation_en": "Georgia, Kakheti",
        "flag": "🇬🇪",
        "country_ru": "Грузия",
        "country_en": "Georgia",
        "grape_ru": "100% Саперави (красильщик)",
        "grape_en": "100% Saperavi",
        "grapes_keys": ["saperavi", "саперави"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.7,
        "acidity": 4.4,
        "tannins": 4.7,
        "tags": ["саперави", "saperavi", "мукузани", "киндзмараули", "грузия"],
        "rationale_ru": "Густой гранатовый цвет, терпкий кизил, ежевика, чернослив, специи и мощные природные танины автохтона.",
        "rationale_en": "Intense tinturier garnet color, tart cornelian cherry, blackberry, prune, and bold authentic Caucasian tannins."
    },

    # ========================== ИГРИСТЫЕ ВИНА ==========================
    {
        "id": "champagne-rose",
        "name_ru": "Розовое Шампанское (Брют)",
        "name_en": "French Champagne Rosé Brut AOC",
        "appellation_ru": "Франция, Шампань",
        "appellation_en": "France, Champagne",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Пино Нуар, Шардоне, Пино Менье",
        "grape_en": "Pinot Noir, Chardonnay, Meunier",
        "grapes_keys": ["пино нуар", "pinot noir", "шампанское", "розе", "розовое", "брют", "champagne", "rose"],
        "color": "розовое",
        "sparkling": True,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 3.2,
        "acidity": 4.8,
        "tannins": 0.3,
        "tags": ["розовое шампанское", "champagne rose", "розе брют", "брют розе", "шампань розе"],
        "rationale_ru": "Классический метод шампанизации: тончайший перляж, лесная земляника, малина, красная смородина и тостовая бриошь.",
        "rationale_en": "Méthode Traditionnelle: fine persistent bead, wild woodland strawberry, raspberry, redcurrant, and warm brioche."
    },
    {
        "id": "prosecco-rose",
        "name_ru": "Итальянское Просекко Розе",
        "name_en": "Italian Prosecco Rosé DOC Millesimato",
        "appellation_ru": "Италия, Венето",
        "appellation_en": "Italy, Veneto",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "Глера, Пино Неро",
        "grape_en": "Glera, Pinot Nero",
        "grapes_keys": ["просекко", "prosecco", "пино неро", "глера", "розе", "rose"],
        "color": "розовое",
        "sparkling": True,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.4,
        "acidity": 4.2,
        "tannins": 0.1,
        "tags": ["просекко розе", "prosecco rose", "итальянское игристое розе"],
        "rationale_ru": "Игристый метод Шарма: сочные красные ягоды, розовый грейпфрут, цветущая сакура и радостный освежающий перляж.",
        "rationale_en": "Vibrant Charmat method: juicy red berries, pink grapefruit zest, cherry blossom, and crisp refreshing effervescence."
    },
    {
        "id": "cava-rose",
        "name_ru": "Испанская Кава Розе Резерва",
        "name_en": "Spanish Cava Rosé Brut Reserva DO",
        "appellation_ru": "Испания, Каталония (Пенедес)",
        "appellation_en": "Spain, Catalonia (Penedès)",
        "flag": "🇪🇸",
        "country_ru": "Испания",
        "country_en": "Spain",
        "grape_ru": "Гарнача, Трепат, Монастрель",
        "grape_en": "Garnacha, Trepat, Monastrell",
        "grapes_keys": ["cava", "кава", "трепат", "гарнача", "розе", "rose"],
        "color": "розовое",
        "sparkling": True,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.9,
        "acidity": 4.5,
        "tannins": 0.2,
        "tags": ["кава розе", "cava rose", "испанское розе игристое"],
        "rationale_ru": "Средиземноморский традиционный метод: спелый гранат, красная смородина, средиземноморские травы и минеральный сухой финиш.",
        "rationale_en": "Traditional bottle-fermented Mediterranean sparkling: ripe pomegranate, redcurrant, garrigue herbs, and dry mineral finish."
    },
    {
        "id": "champagne-brut",
        "name_ru": "Французское Шампанское (Брют)",
        "name_en": "French Champagne Brut AOC",
        "appellation_ru": "Франция, Шампань",
        "appellation_en": "France, Champagne",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Шардоне, Пино Нуар, Пино Менье",
        "grape_en": "Chardonnay, Pinot Noir, Meunier",
        "grapes_keys": ["шампанское", "champagne", "брют", "классический метод"],
        "color": "белое",
        "sparkling": True,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 3.0,
        "acidity": 4.9,
        "tannins": 0.0,
        "tags": ["шампань", "champagne", "брют", "brut", "шампанское"],
        "rationale_ru": "Классический метод шампанизации (Méthode Traditionnelle): тончайший перляж, тона поджаренной бриоши, фундука и хрустящего зеленого яблока.",
        "rationale_en": "Méthode Champenoise excellence: persistent micro-bead, brioche toast, toasted hazelnut, and chalky crisp green apple."
    },
    {
        "id": "franciacorta-docg",
        "name_ru": "Франчакорта DOCG",
        "name_en": "Franciacorta Brut DOCG",
        "appellation_ru": "Италия, Ломбардия",
        "appellation_en": "Italy, Lombardy",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "Шардоне, Пино Неро",
        "grape_en": "Chardonnay, Pinot Nero",
        "grapes_keys": ["франчакорта", "franciacorta", "итальянский метод классика"],
        "color": "белое",
        "sparkling": True,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 3.2,
        "acidity": 4.6,
        "tannins": 0.0,
        "tags": ["франчакорта", "franciacorta", "классическое игристое"],
        "rationale_ru": "Итальянский ответ Шампани: выдержка на осадке, золотистое яблоко, белые цветы, сливочная пенка и благородная сухость.",
        "rationale_en": "Italy's premier traditional method sparkling: prolonged lees aging, golden delicious apple, creamy mousse, and refined dry finish."
    },
    {
        "id": "prosecco-valdobbiadene",
        "name_ru": "Итальянское Просекко Супериоре",
        "name_en": "Valdobbiadene Prosecco Superiore DOCG",
        "appellation_ru": "Италия, Венето",
        "appellation_en": "Italy, Veneto",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "100% Глера",
        "grape_en": "100% Glera",
        "grapes_keys": ["просекко", "prosecco", "глера"],
        "color": "белое",
        "sparkling": True,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.2,
        "acidity": 4.0,
        "tannins": 0.0,
        "tags": ["просекко", "prosecco", "глера", "glera", "шарма"],
        "rationale_ru": "Воздушный метод Шарма: аромат белых персиков, цветущей глицинии, зеленого яблока и освежающие радостные пузырьки.",
        "rationale_en": "Vibrant Charmat style: white peach, wisteria blossom, green apple, and lively refreshing effervescence."
    },
    {
        "id": "cava-reserva",
        "name_ru": "Испанская Кава Резерва",
        "name_en": "Cava Brut Reserva DO",
        "appellation_ru": "Испания, Каталония (Пенедес)",
        "appellation_en": "Spain, Catalonia (Penedès)",
        "flag": "🇪🇸",
        "country_ru": "Испания",
        "country_en": "Spain",
        "grape_ru": "Макабео, Шарелло, Парельяда",
        "grape_en": "Macabeo, Xarel-lo, Parellada",
        "grapes_keys": ["cava", "кава", "испанское игристое"],
        "color": "белое",
        "sparkling": True,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.7,
        "acidity": 4.4,
        "tannins": 0.0,
        "tags": ["кава", "cava", "пенедес", "шарелло"],
        "rationale_ru": "Средиземноморский традиционный метод: минеральный травянистый характер, дымные нюансы, свежий лимон и сухой финиш.",
        "rationale_en": "Traditional Mediterranean method: herbal earthy complexity, smoky undertones, crisp lemon zest, and clean dry palate."
    },

    # ========================== РОЗОВЫЕ ВИНА ==========================
    {
        "id": "provence-rose",
        "name_ru": "Розе Кот де Прованс",
        "name_en": "Côtes de Provence Rosé AOC",
        "appellation_ru": "Франция, Прованс",
        "appellation_en": "France, Provence",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Гренаш, Сенсо, Сира",
        "grape_en": "Grenache, Cinsault, Syrah",
        "grapes_keys": ["provence", "прованс", "розе", "розовое", "rose"],
        "color": "розовое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.4,
        "acidity": 4.2,
        "tannins": 0.5,
        "tags": ["прованс", "provence", "розе", "rose", "розовое вино"],
        "rationale_ru": "Бледно-лососевый оттенок, лесная земляника, белый персик, средиземноморские травы и солоноватая свежесть.",
        "rationale_en": "Pale salmon hue, wild wild strawberry, white nectarine, garrigue herbs, and mouthwatering salinity."
    },

    # ========================== КРЕПЛЕНЫЕ И ДЕСЕРТНЫЕ ==========================
    {
        "id": "porto-tawny",
        "name_ru": "Португальский Портвейн (Тони / Винтаж)",
        "name_en": "Porto Tawny 10/20 Years / Vintage Port",
        "appellation_ru": "Португалия, Долина Дору",
        "appellation_en": "Portugal, Douro Valley",
        "flag": "🇵🇹",
        "country_ru": "Португалия",
        "country_en": "Portugal",
        "grape_ru": "Турига Насьональ, Тинта Рориш",
        "grape_en": "Touriga Nacional, Tinta Roriz",
        "grapes_keys": ["porto", "портвейн", "порту", "дуро", "массандра"],
        "color": "красное",
        "sparkling": False,
        "fortified": True,
        "sweetness": 3,
        "oak": True,
        "body": 5.0,
        "acidity": 3.8,
        "tannins": 3.2,
        "tags": ["портвейн", "porto", "порто", "крепленое", "долина дору"],
        "rationale_ru": "Многолетняя оксидативная выдержка в дубе: инжир, вяленый финик, жареный грецкий орех, карамель и теплое благородство спирта.",
        "rationale_en": "Extended oxidative cask aging: dried fig, medjool date, roasted walnut, toffee caramel, and warming integrated spirit."
    },
    {
        "id": "madeira-boal",
        "name_ru": "Островная Мадера (Боал)",
        "name_en": "Madeira Island Wine (Bual)",
        "appellation_ru": "Португалия, Мадейра",
        "appellation_en": "Portugal, Madeira Island",
        "flag": "🇵🇹",
        "country_ru": "Португалия",
        "country_en": "Portugal",
        "grape_ru": "Боал, Тинта Негра",
        "grape_en": "Bual, Tinta Negra",
        "grapes_keys": ["madeira", "мадера", "крепленое"],
        "color": "белое",
        "sparkling": False,
        "fortified": True,
        "sweetness": 2,
        "oak": True,
        "body": 4.6,
        "acidity": 4.8,
        "tannins": 1.0,
        "tags": ["мадера", "madeira", "островное"],
        "rationale_ru": "Термическая мадеризация (estufagem): каленый орех, цедра горького апельсина, сухофрукты и пронзительная вулканическая кислотность.",
        "rationale_en": "Estufagem thermal aging: roasted hazelnut, Seville orange marmalade, dried fruit, and piercing volcanic acidity."
    }
]


# -----------------------------------------------------------------------------
# 2. Прямой подбор: Российское вино -> До 3-х зарубежных эталонов
# -----------------------------------------------------------------------------

def find_foreign_analogs_for_russian_wine(wine: dict, top_k: int = 3, lang: str = "ru") -> List[dict]:
    """
    Подбирает до 3-х всемирно известных вин-близнецов к российскому вину.
    """
    is_en = (lang == "en")
    w_name = (wine.get("name") or "").lower()
    w_color = (wine.get("color") or wine.get("category") or "").lower()
    w_cat = (wine.get("category") or "").lower()
    w_sugar = str(wine.get("sugar") or wine.get("sweetness") or "").lower()
    w_grape = (wine.get("grape") or "").lower()
    w_desc = (wine.get("description") or "").lower()
    w_feat = wine.get("features") or {}
    w_all = f"{w_name} {w_color} {w_cat} {w_sugar} {w_grape} {w_desc}".lower()

    is_sparkling = bool(w_feat.get("sparkling")) or "игрист" in w_all or "брют" in w_all or "brut" in w_all or "sparkl" in w_all or "шампан" in w_all or "prosecco" in w_all or "cava" in w_all
    is_fortified = "мадер" in w_all or "портвейн" in w_all or "креплен" in w_all or "десертн" in w_all or "porto" in w_all or "madeira" in w_all
    is_rose = "розов" in w_color or "розов" in w_cat or "rose" in w_all or "розе" in w_all
    is_white = ("бел" in w_color or "бел" in w_cat or "white" in w_cat) and not is_rose
    is_red = ("красн" in w_color or "красн" in w_cat or "red" in w_cat) and not is_rose
    has_oak = bool(w_feat.get("oak") or "бочк" in w_desc or "дуб" in w_desc)

    scored_benchmarks = []
    for bm in WORLD_BENCHMARKS:
        # 1. Жесткие фильтры типа (игристое, крепленое)
        if bm["sparkling"] != is_sparkling:
            continue
        if bm["fortified"] != is_fortified:
            continue

        bm_color = bm["color"]
        if not is_sparkling:
            if is_white and "бел" not in bm_color:
                continue
            if is_red and "красн" not in bm_color:
                continue
            if is_rose and "розов" not in bm_color:
                continue

        score = 0.50

        # Сходство цвета для игристых
        if is_sparkling:
            if (is_rose and "розов" in bm_color) or (is_white and "бел" in bm_color):
                score += 0.25
            elif is_rose and "бел" in bm_color:
                score += 0.05

        # Сортовое родство
        matched_grape = any(k in w_grape or k in w_all for k in bm["grapes_keys"])
        if matched_grape:
            score += 0.32

        # Сходство по дубовой выдержке
        if bm["oak"] == has_oak:
            score += 0.10

        # Сенсорная близость
        try:
            w_acid = float(w_feat.get("acidity") or 3.8)
            w_tann = float(w_feat.get("tannin") or 2.5)
            w_body = float(w_feat.get("body") or 3.2)
            dist = abs(w_acid - bm["acidity"]) * 0.3 + abs(w_tann - bm["tannins"]) * 0.3 + abs(w_body - bm["body"]) * 0.2
            score += max(0.0, 0.12 - dist * 0.04)
        except Exception:
            score += 0.05

        similarity_pct = int(min(98, max(85, round(score * 100))))

        explanation = bm["rationale_en"] if is_en else bm["rationale_ru"]
        name_disp = bm["name_en"] if is_en else bm["name_ru"]
        app_disp = bm["appellation_en"] if is_en else bm["appellation_ru"]
        grape_disp = bm["grape_en"] if is_en else bm["grape_ru"]

        scored_benchmarks.append({
            "id": bm["id"],
            "name": name_disp,
            "appellation": app_disp,
            "flag": bm["flag"],
            "country": bm["country_en"] if is_en else bm["country_ru"],
            "grape": grape_disp,
            "similarity": similarity_pct,
            "explanation": explanation,
            "rationale": explanation,
            "style_badge": "Мировой аналог" if not is_en else "World Benchmark Twin",
            "body": bm["body"],
            "acidity": bm["acidity"],
            "tannins": bm["tannins"]
        })

    scored_benchmarks.sort(key=lambda x: x["similarity"], reverse=True)
    if not scored_benchmarks:
        # Fallback на проверенные мировые эталоны в зависимости от стиля
        pool = [b for b in WORLD_BENCHMARKS if b["sparkling"] == is_sparkling] or WORLD_BENCHMARKS
        for bm in pool[:top_k]:
            explanation = bm["rationale_en"] if is_en else bm["rationale_ru"]
            scored_benchmarks.append({
                "id": bm["id"],
                "name": bm["name_en"] if is_en else bm["name_ru"],
                "appellation": bm["appellation_en"] if is_en else bm["appellation_ru"],
                "flag": bm["flag"],
                "country": bm["country_en"] if is_en else bm["country_ru"],
                "grape": bm["grape_en"] if is_en else bm["grape_ru"],
                "similarity": 88,
                "explanation": explanation,
                "rationale": explanation,
                "style_badge": "Мировой аналог" if not is_en else "World Benchmark Twin",
                "body": bm["body"],
                "acidity": bm["acidity"],
                "tannins": bm["tannins"]
            })
    return scored_benchmarks[:top_k]


# -----------------------------------------------------------------------------
# 3. Обратный поиск: Зарубежное вино -> Топ-3 Российских вин из каталога
# -----------------------------------------------------------------------------

def find_russian_analogs_for_foreign_query(query: str, catalog_wines: List[dict], top_k: int = 3, lang: str = "ru") -> Dict[str, Any]:
    """
    Принимает название зарубежного вина (например «Шабли», «Chablis», «Кьянти», «Бордо»)
    и находит до 3-х лучших российских вин из каталога 2108 позиций.
    Обеспечивает разнообразие виноделен (дедупликация) и строго top_k <= 3.
    """
    is_en = (lang == "en")
    q = query.strip().lower()
    if not q:
        return {"foreign": None, "russian_analogs": []}

    # 1. Находим зарубежный эталон по тегам, сортам, названиям на RU и EN
    matched_bm = None
    for bm in WORLD_BENCHMARKS:
        searchable_terms = bm["tags"] + bm["grapes_keys"] + [
            bm["name_ru"].lower(),
            bm["name_en"].lower(),
            bm["id"].replace("-", " ")
        ]
        for term in searchable_terms:
            t = term.lower()
            if t in q or q in t:
                matched_bm = bm
                break
        if matched_bm:
            break

    # Дефолтный fallback эталон
    if not matched_bm:
        if any(w in q for w in ["red", "красн", "мерло", "каберне", "шираз", "сира"]):
            matched_bm = next(b for b in WORLD_BENCHMARKS if b["id"] == "bordeaux-medoc")
        elif any(w in q for w in ["sparkl", "игрист", "брют", "шампан"]):
            matched_bm = next(b for b in WORLD_BENCHMARKS if b["id"] == "champagne-brut")
        elif any(w in q for w in ["rose", "розов", "розе"]):
            matched_bm = next(b for b in WORLD_BENCHMARKS if b["id"] == "provence-rose")
        else:
            matched_bm = next(b for b in WORLD_BENCHMARKS if b["id"] == "chablis-premier-cru")

    # 2. Ищем близкие российские вина в каталоге
    is_target_white = "бел" in matched_bm["color"]
    is_target_red = "красн" in matched_bm["color"]
    is_target_rose = "розов" in matched_bm["color"]
    is_target_sparkling = matched_bm["sparkling"]
    is_target_fortified = matched_bm["fortified"]
    target_grapes = matched_bm["grapes_keys"]
    target_oak = matched_bm["oak"]

    scored_wines = []
    seen_wineries = set()

    for w in catalog_wines:
        w_id = w.get("id") or w.get("slug")
        w_name = (w.get("name") or "").strip()
        w_color = (w.get("color") or w.get("category") or "").lower()
        w_cat = (w.get("category") or "").lower()
        w_grape = (w.get("grape") or "").lower()
        w_desc = (w.get("description") or "").lower()
        w_winery = (w.get("winery") or "").strip()
        w_feat = w.get("features") or {}
        w_all = f"{w_name} {w_color} {w_cat} {w_grape} {w_desc}".lower()

        w_sparkling = bool(w_feat.get("sparkling")) or "игрист" in w_all or "брют" in w_all
        if w_sparkling != is_target_sparkling:
            continue

        w_fort = "мадер" in w_all or "портвейн" in w_all or "креплен" in w_all or "десертн" in w_all
        if w_fort != is_target_fortified:
            continue

        # Проверка цвета
        if is_target_white:
            if not ("бел" in w_color or "бел" in w_cat or "white" in w_cat):
                continue
        elif is_target_red:
            if not ("красн" in w_color or "красн" in w_cat or "red" in w_cat):
                continue
        elif is_target_rose:
            if not ("розов" in w_color or "розов" in w_cat or "rose" in w_cat):
                continue

        score = 0.50

        # Сортовое совпадение
        has_grape = any(gk in w_grape or gk in w_all for gk in target_grapes)
        if has_grape:
            score += 0.35

        # Совпадение по дубовой выдержке
        w_has_oak = bool(w_feat.get("oak") or "бочк" in w_desc or "дуб" in w_desc)
        if w_has_oak == target_oak:
            score += 0.10

        # Сенсорика
        try:
            w_acid = float(w_feat.get("acidity") or 3.8)
            w_tann = float(w_feat.get("tannin") or 2.5)
            w_body = float(w_feat.get("body") or 3.2)
            dist = abs(w_acid - matched_bm["acidity"]) * 0.3 + abs(w_tann - matched_bm["tannins"]) * 0.3 + abs(w_body - matched_bm["body"]) * 0.2
            score += max(0.0, 0.12 - dist * 0.04)
        except Exception:
            w_acid, w_body = 3.8, 3.2
            score += 0.05

        norm_score = int(min(98, max(85, round(score * 100))))

        bm_title = matched_bm["name_en"] if is_en else matched_bm["name_ru"]
        grape_disp = matched_bm["grape_en"] if is_en else matched_bm["grape_ru"]
        if is_en:
            reason = f"Russian twin for «{bm_title}»: matching {grape_disp} profile, balanced acidity ({w_acid:.1f}/5) and harmonious body ({w_body:.1f}/5)."
            role_label = "Russian Twin"
        else:
            reason = f"Российский близнец «{bm_title}»: точное попадание в сортовой профиль ({grape_disp}), баланс кислотности ({w_acid:.1f}/5) и структуры тела ({w_body:.1f}/5)."
            role_label = "Российский аналог"

        scored_wines.append({
            "id": w_id,
            "slug": w_id,
            "name": w_name,
            "winery": w_winery or ("Russian Winery" if is_en else "Российская винодельня"),
            "region": w.get("region") or ("Russia" if is_en else "Россия"),
            "score": norm_score,
            "role": role_label,
            "explanation": reason,
            "image_url": w.get("image_url") or f"/api/image/{w_id}",
            "grape": w.get("grape") or grape_disp,
            "color": w.get("color") or matched_bm["color"],
        })

    # Сортируем по убыванию сходства
    scored_wines.sort(key=lambda x: x["score"], reverse=True)

    # Дедупликация по винодельне и названию: отбираем до top_k вин от РАЗНЫХ виноделен
    top_analogs = []
    seen_winery_keys = set()
    seen_names = set()

    for w in scored_wines:
        w_winery = w["winery"].lower()
        w_name_clean = w["name"].lower()
        if w_winery in seen_winery_keys or w_name_clean in seen_names:
            continue
        seen_winery_keys.add(w_winery)
        seen_names.add(w_name_clean)
        top_analogs.append(w)
        if len(top_analogs) >= top_k:
            break

    # Если уникальных виноделен не набралось 3, добираем из оставшихся
    if len(top_analogs) < top_k:
        for w in scored_wines:
            if w not in top_analogs:
                top_analogs.append(w)
                if len(top_analogs) >= top_k:
                    break

    foreign_info = {
        "id": matched_bm["id"],
        "name": matched_bm["name_en"] if is_en else matched_bm["name_ru"],
        "appellation": matched_bm["appellation_en"] if is_en else matched_bm["appellation_ru"],
        "flag": matched_bm["flag"],
        "grape": matched_bm["grape_en"] if is_en else matched_bm["grape_ru"],
        "explanation": matched_bm["rationale_en"] if is_en else matched_bm["rationale_ru"]
    }

    return {
        "foreign": foreign_info,
        "russian_analogs": top_analogs[:top_k],
        "total": len(top_analogs[:top_k])
    }
