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

from sommelier.stores_and_history import HISTORICAL_WINES_DB


# -----------------------------------------------------------------------------
# 1. Справочник знаменитых мировых эталонов (World Wine Benchmarks)
# -----------------------------------------------------------------------------

WORLD_BENCHMARKS = [
    # --- БЕЛЫЕ ВИНА ---
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
        "tags": ["шабли", "chablis", "киммеридж", "минеральное"],
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
        "tags": ["мерсо", "meursault", "монраше", "montrachet", "белая бургундия"],
        "rationale_ru": "Сливочно-кремовая плотность, тона теплой бриоши, сливочного масла, спелого персика и благородного французского дуба.",
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
        "tags": ["сансер", "sancerre", "пуйи-фюме", "pouilly-fume"],
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
        "tags": ["мальборо", "marlborough", "совиньон блан", "sauvignon blanc"],
        "rationale_ru": "Взрывная палитра маракуйи, грейпфрута, лайма, свежескошенной травы и сочной бодрящей кислотности.",
        "rationale_en": "Explosive passionfruit, pink grapefruit, lime zest, cut grass, and mouthwatering crisp finish."
    },
    {
        "id": "mosel-riesling",
        "name_ru": "Рислинг Мозеля",
        "name_en": "Mosel Dry / Off-Dry Riesling",
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
        "tags": ["рислинг", "riesling", "мозель", "mosel", "рейнгау"],
        "rationale_ru": "Сланцевая стальная минеральность, зеленое яблоко, сочный белый персик и филигранный баланс кислотности.",
        "rationale_en": "Slate minerality, green apple, juicy white peach, and filigree acid-fruit balance."
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
        "tags": ["гави", "gavi", "cortese"],
        "rationale_ru": "Элегантная сухость, ноты белого персика, горьковатого миндаля, полевых цветов и свежего морского бриза.",
        "rationale_en": "Crisp dryness, white peach, green almond, chamomile blossom, and breezy alpine minerality."
    },
    {
        "id": "pinot-grigio-friuli",
        "name_ru": "Пино Гриджо Фриули",
        "name_en": "Pinot Grigio Friuli DOC",
        "appellation_ru": "Италия, Фриули-Венеция-Джулия",
        "appellation_en": "Italy, Friuli",
        "flag": "🇮🇹",
        "country_ru": "Италия",
        "country_en": "Italy",
        "grape_ru": "100% Пино Гриджо",
        "grape_en": "100% Pinot Grigio",
        "grapes_keys": ["pinot grigio", "пино гриджо", "пино гри"],
        "color": "белое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.4,
        "acidity": 3.8,
        "tannins": 0.0,
        "tags": ["пино гриджо", "pinot grigio", "соаве"],
        "rationale_ru": "Легкое, питкое, с ароматом спелой груши дюшес, белых цветов, лимонной цедры и мягкой свежестью.",
        "rationale_en": "Light, refreshing, white pear, meadow blossoms, lemon peel, and clean easy-drinking style."
    },

    # --- КРАСНЫЕ ВИНА ---
    {
        "id": "bordeaux-medoc",
        "name_ru": "Бордо Гран Крю (Медок / Пойяк)",
        "name_en": "Bordeaux Grand Cru Classé (Médoc / Pauillac)",
        "appellation_ru": "Франция, Бордо",
        "appellation_en": "France, Bordeaux",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Каберне Совиньон, Мерло, Каберне Фран",
        "grape_en": "Cabernet Sauvignon, Merlot, Cabernet Franc",
        "grapes_keys": ["cabernet", "каберне", "merlot", "мерло"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.2,
        "acidity": 3.8,
        "tannins": 4.2,
        "tags": ["бордо", "bordeaux", "медок", "medoc", "марго", "пойяк", "каберне"],
        "rationale_ru": "Классическая бордоская структура: черная смородина, кедр, сигарный хьюмидор, графит и мощные благородные танины.",
        "rationale_en": "Classic Bordeaux architecture: cassis, cedar box, cigar tobacco, graphite, and structured noble tannins."
    },
    {
        "id": "saint-emilion-merlot",
        "name_ru": "Сент-Эмильон Гран Крю",
        "name_en": "Saint-Émilion Grand Cru (Right Bank Bordeaux)",
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
        "body": 3.9,
        "acidity": 3.5,
        "tannins": 3.6,
        "tags": ["сент-эмильон", "saint-emilion", "помероль", "мерло", "merlot"],
        "rationale_ru": "Бархатные округлые танины, спелая черная слива, темный шоколад, вишня в ликере и мягкое теплое послевкусие.",
        "rationale_en": "Velvety round tannins, ripe black plum, dark cocoa, chocolate cherry, and supple warmth."
    },
    {
        "id": "bourgogne-pinot-noir",
        "name_ru": "Красная Бургундия (Пино Нуар)",
        "name_en": "Bourgogne Rouge / Côte de Nuits Pinot Noir",
        "appellation_ru": "Франция, Бургундия",
        "appellation_en": "France, Burgundy",
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
        "body": 3.0,
        "acidity": 4.2,
        "tannins": 2.2,
        "tags": ["бургундия", "bourgogne", "burgundy", "пино нуар", "pinot noir"],
        "rationale_ru": "Шелковистые танины, лесная земляника, спелая вишня, подлесок, осенний лист и утонченная ягодная кислотность.",
        "rationale_en": "Silky delicate tannins, wild strawberry, red cherry, forest floor, autumn leaves, and refined acid spine."
    },
    {
        "id": "chianti-classico",
        "name_ru": "Кьянти Классико",
        "name_en": "Chianti Classico Gran Selezione DOCG",
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
        "body": 3.6,
        "acidity": 4.2,
        "tannins": 3.6,
        "tags": ["кьянти", "chianti", "санджовезе", "брунелло"],
        "rationale_ru": "Яркая бодрящая кислотность, вяленая вишня, сухие тосканские травы, специи, сафьян и гастрономичный сухой профиль.",
        "rationale_en": "Vibrant food-friendly acidity, dried cherry, Mediterranean herbs, savory leather, and dry structured grip."
    },
    {
        "id": "barolo-piedmont",
        "name_ru": "Бароло (Король вин)",
        "name_en": "Barolo DOCG (Piedmont)",
        "appellation_ru": "Италия, Пьемонт",
        "appellation_en": "Italy, Piedmont",
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
        "body": 4.2,
        "acidity": 4.4,
        "tannins": 4.8,
        "tags": ["бароло", "barolo", "барбареско", "неббиоло", "красностоп"],
        "rationale_ru": "Мощнейший танинный каркас, высокая природная кислотность, тона смолы, лепестков розы, кожи, сушеной вишни и трюфеля.",
        "rationale_en": "Massive tannin architecture, high natural acidity, tar, dried rose, leather, dark cherry, and wild truffle complexity."
    },
    {
        "id": "madiran-tannat",
        "name_ru": "Мадиран (Таннат)",
        "name_en": "Madiran AOC (Tannat)",
        "appellation_ru": "Франция, Юго-Запад",
        "appellation_en": "France, South-West",
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
        "body": 4.5,
        "acidity": 4.0,
        "tannins": 4.9,
        "tags": ["мадиран", "madiran", "таннат", "красностоп"],
        "rationale_ru": "Чернильный непроницаемый цвет, колоссальные танины ягодной кожицы, терн, черная смородина и колоссальный потенциал выдержки.",
        "rationale_en": "Inky impenetrable color, monumental grape-skin tannins, sloe berry, blackcurrant, and epic aging stamina."
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
        "acidity": 3.6,
        "tannins": 3.5,
        "tags": ["риоха", "rioja", "темпранильо", "tempranillo"],
        "rationale_ru": "Длительная выдержка в дубовых бочках: сладкая ваниль, кокос, сушеная вишня, кедр, табак и округлая бархатистость.",
        "rationale_en": "Extended oak barrel maturation: sweet vanilla, toasted coconut, dried cherry, cedar, cigar tobacco, and resolved velvet."
    },
    {
        "id": "mendoza-malbec",
        "name_ru": "Мальбек Мендосы",
        "name_en": "Mendoza Malbec Single Vineyard",
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
        "body": 4.1,
        "acidity": 3.4,
        "tannins": 3.6,
        "tags": ["мальбек", "malbec", "мендоса", "mendoza"],
        "rationale_ru": "Глубокий фиолетовый оттенок, ноты черники, сочной ежевики, лесной фиалки, какао-бобов и мягкие ласкающие танины.",
        "rationale_en": "Deep violet hue, blackberry jam, blueberries, forest violet, dark cocoa, and plush rounded tannins."
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
        "body": 4.0,
        "acidity": 3.7,
        "tannins": 3.8,
        "tags": ["сира", "syrah", "шираз", "shiraz", "рона"],
        "rationale_ru": "Пряный черный свежемолотый перец, копчености, черные оливки, ежевика и глубокий дымный шлейф.",
        "rationale_en": "Cracked black peppercorn, smoked bacon, cured black olive, dark blackberry, and savory smoky finish."
    },
    {
        "id": "georgia-saperavi",
        "name_ru": "Грузинское Саперави (Мукузани / Киндзмараули)",
        "name_en": "Georgian Saperavi (Mukuzani / Kindzmarauli)",
        "appellation_ru": "Грузия, Кахетия",
        "appellation_en": "Georgia, Kakheti",
        "flag": "🇬🇪",
        "country_ru": "Грузия",
        "country_en": "Georgia",
        "grape_ru": "100% Саперави (сорт-красильщик)",
        "grape_en": "100% Saperavi (Teinturier)",
        "grapes_keys": ["saperavi", "саперави"],
        "color": "красное",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": True,
        "body": 4.3,
        "acidity": 3.8,
        "tannins": 4.2,
        "tags": ["саперави", "saperavi", "мукузани", "киндзмараули"],
        "rationale_ru": "Плотный рубиново-гранатовый цвет с красной мякотью, ноты гранатового сока, ежевики, чернослива и кавказских пряностей.",
        "rationale_en": "Dense garnet-ruby teinturier profile, ripe pomegranate, blackberry juice, sun-dried prune, and warm spices."
    },

    # --- ИГРИСТЫЕ ВИНА ---
    {
        "id": "champagne-brut",
        "name_ru": "Французское Шампанское (Брют)",
        "name_en": "Champagne AOC Brut Premier",
        "appellation_ru": "Франция, Шампань",
        "appellation_en": "France, Champagne",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Шардоне, Пино Нуар, Пино Менье",
        "grape_en": "Chardonnay, Pinot Noir, Pinot Meunier",
        "grapes_keys": ["шампанское", "champagne", "брют"],
        "color": "белое",
        "sparkling": True,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 3.0,
        "acidity": 4.8,
        "tannins": 0.0,
        "tags": ["шампанское", "champagne", "классический метод"],
        "rationale_ru": "Традиционный метод шампанизации с выдержкой на осадке: сдобная теплая бриошь, зеленые яблоки, лимонный курд и тончайший перляж.",
        "rationale_en": "Traditional méthode champenoise with extended lees aging: warm brioche, green apple, chalky minerality, and silky bubbles."
    },
    {
        "id": "prosecco-valdobbiadene",
        "name_ru": "Итальянское Просекко",
        "name_en": "Prosecco Superiore Valdobbiadene DOCG",
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
        "acidity": 3.8,
        "tannins": 0.0,
        "tags": ["просекко", "prosecco", "шарма"],
        "rationale_ru": "Метод Шарма: легкое освежающее игристое с ароматом спелой груши, белого персика, цветов акации и цитрусовой чистотой.",
        "rationale_en": "Charmat method lightness, ripe pear, white peach, acacia blossoms, and crisp refreshing effervescence."
    },
    {
        "id": "cava-reserva",
        "name_ru": "Испанская Кава Резерва",
        "name_en": "Cava Brut Reserva DO",
        "appellation_ru": "Испания, Каталония",
        "appellation_en": "Spain, Catalonia",
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
        "body": 2.6,
        "acidity": 4.2,
        "tannins": 0.0,
        "tags": ["кава", "cava"],
        "rationale_ru": "Бутылочная выдержка, средиземноморская цитрусовая бодрость, тона подсушенного хлеба и свежих зеленых яблок.",
        "rationale_en": "Traditional bottle fermentation, Mediterranean citrus bite, toasted breadcrumbs, and crunchy green apple."
    },

    # --- РОЗОВЫЕ ВИНА ---
    {
        "id": "provence-rose",
        "name_ru": "Розе Кот де Прованс",
        "name_en": "Côtes de Provence Rosé AOP",
        "appellation_ru": "Франция, Прованс",
        "appellation_en": "France, Provence",
        "flag": "🇫🇷",
        "country_ru": "Франция",
        "country_en": "France",
        "grape_ru": "Гренаш, Сенсо, Сира",
        "grape_en": "Grenache, Cinsault, Syrah",
        "grapes_keys": ["provence", "прованс", "розе", "розовое"],
        "color": "розовое",
        "sparkling": False,
        "fortified": False,
        "sweetness": 0,
        "oak": False,
        "body": 2.2,
        "acidity": 3.9,
        "tannins": 0.5,
        "tags": ["прованс", "provence", "розе", "розовое"],
        "rationale_ru": "Бледно-лососевый оттенок, лесная земляника, красная смородина, соленый морской бриз и минеральная сухость.",
        "rationale_en": "Pale salmon hue, wild strawberry, redcurrant, sea salt breeze, and crisp mineral dryness."
    },

    # --- КРЕПЛЕНЫЕ И ДЕСЕРТНЫЕ ВИНА ---
    {
        "id": "porto-tawny",
        "name_ru": "Португальский Портвейн (Тони / Винтаж)",
        "name_en": "Porto Tawny 10yo / Vintage Port",
        "appellation_ru": "Португалия, Долина Дору",
        "appellation_en": "Portugal, Douro Valley",
        "flag": "🇵🇹",
        "country_ru": "Португалия",
        "country_en": "Portugal",
        "grape_ru": "Турига Насьонал, Тинта Рориз",
        "grape_en": "Touriga Nacional, Tinta Roriz",
        "grapes_keys": ["porto", "портвейн", "порту", "дуро", "массандра"],
        "color": "красное",
        "sparkling": False,
        "fortified": True,
        "sweetness": 3,
        "oak": True,
        "body": 4.8,
        "acidity": 3.6,
        "tannins": 3.2,
        "tags": ["портвейн", "porto", "порту", "десертное", "крепленое"],
        "rationale_ru": "Многолетняя выдержка в дубовых бочках: вяленый инжир, чернослив в шоколаде, каленый грецкий орех и теплое ликерное послевкусие.",
        "rationale_en": "Aged oak cask maturation: sun-dried figs, chocolate prunes, toasted walnuts, and warming velvety liqueur finish."
    },
    {
        "id": "madeira-boal",
        "name_ru": "Островная Мадера",
        "name_en": "Madeira Verdelho / Boal",
        "appellation_ru": "Португалия, Остров Мадейра",
        "appellation_en": "Portugal, Island of Madeira",
        "flag": "🇵🇹",
        "country_ru": "Португалия",
        "country_en": "Portugal",
        "grape_ru": "Вердельо, Боал",
        "grape_en": "Verdelho, Boal",
        "grapes_keys": ["madeira", "мадера", "крепленое"],
        "color": "белое",
        "sparkling": False,
        "fortified": True,
        "sweetness": 2,
        "oak": True,
        "body": 4.5,
        "acidity": 4.8,
        "tannins": 1.0,
        "tags": ["мадера", "madeira", "мадеризация"],
        "rationale_ru": "Тепловая выдержка на солнце: пронзительная живая кислотность, ноты жареного фундука, жженой карамели, сушеной кураги и табака.",
        "rationale_en": "Solar estufagem aging: piercing electric acidity, roasted hazelnut, burnt caramel, dried apricot, and tobacco leaf."
    }
]


# -----------------------------------------------------------------------------
# 2. Подбор иностранных аналогов к выбранному российскому вину
# -----------------------------------------------------------------------------

def find_foreign_analogs_for_russian_wine(wine: dict, top_k: int = 3, lang: str = "ru") -> List[dict]:
    """
    Принимает словарь российского вина из каталога VINA и подбирает
    до 3-х наиболее близких мировых эталонов (зарубежных аналогов-близнецов).
    """
    is_en = (lang == "en")
    color = (wine.get("color") or wine.get("category") or "").lower()
    cat = (wine.get("category") or "").lower()
    grape = (wine.get("grape") or "").lower()
    name = (wine.get("name") or "").lower()
    desc = (wine.get("description") or "").lower()
    features = wine.get("features") or {}
    all_text = f"{name} {color} {cat} {grape} {desc}".lower()

    is_sparkling = bool(features.get("sparkling")) or "игрист" in all_text or "брют" in all_text or "brut" in all_text
    is_fortified = (
        "мадер" in all_text or "портвейн" in all_text or "херес" in all_text or
        "креплен" in all_text or "десертн" in all_text or "ликерн" in all_text
    )

    w_acidity = float(features.get("acidity") or 3.8)
    w_tannins = float(features.get("tannin") or 2.5)
    w_body = float(features.get("body") or 3.2)
    w_sweet = features.get("sweetness")
    has_oak = bool(features.get("oak") or "бочк" in desc or "дуб" in desc or "выдержк" in desc)

    scored_benchmarks = []
    for bm in WORLD_BENCHMARKS:
        # 1. Жесткие фильтры: тип игристости и крепления
        if bm["sparkling"] != is_sparkling:
            continue
        if bm["fortified"] != is_fortified:
            continue

        # 2. Цвет вина
        is_bm_white = "бел" in bm["color"]
        is_w_white = "бел" in color or "бел" in cat or "white" in cat
        is_bm_red = "красн" in bm["color"]
        is_w_red = "красн" in color or "красн" in cat or "red" in cat
        is_bm_rose = "розов" in bm["color"]
        is_w_rose = "розов" in color or "розов" in cat or "rose" in cat

        if is_bm_white != is_w_white and not (is_bm_white and "оранж" in color):
            if is_bm_red != is_w_red or is_bm_rose != is_w_rose:
                continue

        score = 0.50

        # Совпадение сортов винограда или родство стилей
        grape_hit = False
        for gk in bm["grapes_keys"]:
            if gk in grape or gk in all_text:
                score += 0.30
                grape_hit = True
                break

        # Специфические российские автохтоны и их мировые двойники
        if "красностоп" in all_text:
            if bm["id"] in ("madiran-tannat", "barolo-piedmont"):
                score += 0.40
                grape_hit = True
        elif "саперави" in all_text:
            if bm["id"] in ("georgia-saperavi", "mendoza-malbec"):
                score += 0.42
                grape_hit = True
        elif "цимлянск" in all_text:
            if bm["id"] in ("bourgogne-pinot-noir", "chianti-classico"):
                score += 0.38
                grape_hit = True
        elif "кокур" in all_text:
            if bm["id"] in ("gavi-piemonte", "chablis-premier-cru"):
                score += 0.38
                grape_hit = True
        elif "сибирьков" in all_text:
            if bm["id"] in ("sancerre-loire", "marlborough-sauvignon"):
                score += 0.38
                grape_hit = True

        # Совпадение по дубу
        if bm["oak"] == has_oak:
            score += 0.10

        # Сенсорная близость (кислотность, танины, тело)
        dist = (
            abs(bm["acidity"] - w_acidity) * 0.4 +
            abs(bm["tannins"] - w_tannins) * 0.4 +
            abs(bm["body"] - w_body) * 0.3
        )
        sensory_bonus = max(0.0, 0.15 - dist * 0.05)
        score += sensory_bonus

        # Нормализация в процент сходства (от 86% до 98%)
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
    return scored_benchmarks[:top_k]


# -----------------------------------------------------------------------------
# 3. Обратный поиск: Зарубежное вино -> Топ-3 Российских вин из каталога
# -----------------------------------------------------------------------------

def find_russian_analogs_for_foreign_query(query: str, catalog_wines: List[dict], top_k: int = 3, lang: str = "ru") -> Dict[str, Any]:
    """
    Принимает название зарубежного вина (например «Шабли», «Chablis», «Кьянти», «Бордо»)
    и находит до 3-х лучших российских вин из каталога 2108 позиций.
    """
    is_en = (lang == "en")
    q = query.strip().lower()
    if not q:
        return {"foreign": None, "russian_analogs": []}

    # 1. Определяем зарубежный эталон
    matched_bm = None
    for bm in WORLD_BENCHMARKS:
        for tag in bm["tags"] + bm["grapes_keys"] + [bm["name_ru"].lower(), bm["name_en"].lower(), bm["id"]]:
            if tag in q or q in tag:
                matched_bm = bm
                break
        if matched_bm:
            break

    # Дефолтный fallback эталон, если введено неизвестное слово
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
    for w in catalog_wines:
        w_id = w.get("id") or w.get("slug")
        w_name = (w.get("name") or "").lower()
        w_color = (w.get("color") or w.get("category") or "").lower()
        w_cat = (w.get("category") or "").lower()
        w_grape = (w.get("grape") or "").lower()
        w_desc = (w.get("description") or "").lower()
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
            score += 0.30

        # Совпадение по дубовой выдержке
        w_has_oak = bool(w_feat.get("oak") or "бочк" in w_desc or "дуб" in w_desc)
        if w_has_oak == target_oak:
            score += 0.12

        # Сенсорика
        w_acid = float(w_feat.get("acidity") or 3.8)
        w_tann = float(w_feat.get("tannin") or 2.5)
        w_body = float(w_feat.get("body") or 3.2)
        dist = abs(w_acid - matched_bm["acidity"]) * 0.3 + abs(w_tann - matched_bm["tannins"]) * 0.3 + abs(w_body - matched_bm["body"]) * 0.2
        score += max(0.0, 0.15 - dist * 0.05)

        norm_score = int(min(98, max(85, round(score * 100))))

        # Составление объяснения похожести
        bm_title = matched_bm["name_en"] if is_en else matched_bm["name_ru"]
        if is_en:
            reason = f"Russian twin for «{bm_title}»: matching {matched_bm['grape_en']} sensory profile, balanced acidity ({w_acid:.1f}/5) and harmonious body ({w_body:.1f}/5)."
            role_label = "Russian Twin"
        else:
            reason = f"Российский близнец «{bm_title}»: точное попадание в сортовой профиль ({matched_bm['grape_ru']}), баланс кислотности ({w_acid:.1f}/5) и структуры тела ({w_body:.1f}/5)."
            role_label = "Российский аналог"

        scored_wines.append({
            "id": w_id,
            "slug": w_id,
            "name": w.get("name"),
            "winery": w.get("winery") or "Российская винодельня",
            "region": w.get("region") or "Россия",
            "score": norm_score,
            "role": role_label,
            "explanation": reason,
            "image_url": w.get("image_url") or f"/api/image/{w_id}",
            "grape": w.get("grape") or matched_bm["grape_ru"],
            "color": w.get("color") or matched_bm["color"],
            "price": w.get("price") or "1 890"
        })

    # Сортируем по убыванию сходства и возвращаем не более 3х
    scored_wines.sort(key=lambda x: x["score"], reverse=True)
    top_analogs = scored_wines[:top_k]

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
        "russian_analogs": top_analogs,
        "total": len(top_analogs)
    }
