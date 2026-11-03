"""
VINA - Экспертный гастрономический модуль сомелье:
- Подбор блюд к выбранному вину (Wine -> Food Pairing)
- Детальный вкусовой профиль (кислотность, танины, тело, ароматика)
- Подбор близких аналогов в российском каталоге
- Распознавание интентов пользователя без раздражающих встречных вопросов
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from sommelier.stores_and_history import HISTORICAL_WINES_DB, get_simple_and_unusual_dishes


# -----------------------------------------------------------------------------
# 1. Определение интентов пользователя
# -----------------------------------------------------------------------------

def is_food_pairing_query(text: str) -> bool:
    """Определяет вопрос о гастропарах / блюдах / еде / кухне к вину (на русском и английском)."""
    t = text.lower().strip()
    patterns = [
        r"к каком[уи] блюд",
        r"к каким блюд",
        r"с чем пода[тв]",
        r"с чем пить",
        r"с чем есть",
        r"с чем употребл",
        r"с чем сочета[етс]",
        r"как[аи][яе] ед[ае]",
        r"как[аи][еы] блюд",
        r"как[аи][яе] кухн",
        r"гастропар",
        r"гастрономическ",
        r"закуск",
        r"к чему подход",
        r"под какое блюдо",
        r"под какую еду",
        r"чем закус",
        r"что к нему подать",
        r"что подать к",
        r"с какой едой",
        r"что приготовить",
        # English patterns
        r"what to pair",
        r"pair with",
        r"food pairing",
        r"food pair",
        r"what dish",
        r"which dish",
        r"serve with",
        r"what food",
        r"pairing",
        r"what to eat",
        r"what to drink with",
        r"pair this wine",
    ]
    for p in patterns:
        if re.search(p, t):
            return True
    return False


def is_taste_profile_query(text: str) -> bool:
    """Определяет вопрос о вкусе / кислотности / танинах / ароматике вина (на русском и английском)."""
    t = text.lower().strip()
    patterns = [
        r"профиль вкус",
        r"опиши вкус",
        r"каков вкус",
        r"какой вкус",
        r"кислотност.*танин",
        r"танин.*кислотност",
        r"опиши.*танин",
        r"опиши.*кислотност",
        r"вкус.*аромат",
        r"органолептич",
        r"какие танины",
        r"какая кислотность",
        r"дегустационн",
        # English patterns
        r"flavor profile",
        r"taste profile",
        r"describe taste",
        r"taste and aroma",
        r"acidity and tannin",
        r"tannins and acidity",
        r"how does it taste",
        r"taste profile",
        r"flavor",
    ]
    for p in patterns:
        if re.search(p, t):
            return True
    return False


def is_analogs_query(text: str) -> bool:
    """Определяет запрос на поиск похожих вин / аналогов (на русском и английском)."""
    t = text.lower().strip()
    patterns = [
        r"аналог",
        r"похож.*вин",
        r"что похоже",
        r"альтернатив",
        r"замен.*этом",
        r"похожие по вкусу",
        r"найти похож",
        # English patterns
        r"analog",
        r"similar.*wine",
        r"find.*similar",
        r"similar to",
        r"alternative",
        r"substitute",
        r"find analogs",
        r"wines like",
    ]
    for p in patterns:
        if re.search(p, t):
            return True
    return False


# -----------------------------------------------------------------------------
# 2. Поиск вина по slug или тексту
# -----------------------------------------------------------------------------

STOP_WORDS = {
    "каком", "какому", "какая", "какое", "какие", "блюду", "блюда", "блюдам", "подходит", "сочетается",
    "подать", "пить", "есть", "опиши", "вкус", "танины", "кислотность", "подбери", "похожих", "вина",
    "вино", "российских", "аналоги", "этом", "этому", "это", "этот", "этого", "подскажи", "скажи",
    "хорошо", "будет", "профиль", "кухня", "кухни"
}


def find_wine_in_catalog(by_id: dict, wines_list: list, slug_or_text: str | None) -> dict | None:
    """Находит карточку вина в базе по slug или названию с поддержкой синонимов."""
    if not slug_or_text:
        return None
    s = slug_or_text.strip().lower()

    # 1. Прямой поиск по ID
    if s in by_id:
        return by_id[s]

    # 2. Поиск в HISTORICAL_WINES_DB по прямому ключу
    hist = HISTORICAL_WINES_DB.get(s)
    if hist:
        for w in wines_list:
            if hist.wine_name.lower() in w["name"].lower() or ("мадер" in hist.wine_name.lower() and "мадер" in w["name"].lower()):
                return w
        return {
            "id": hist.wine_slug,
            "name": hist.wine_name,
            "winery": hist.founder,
            "category": "Крепленое",
            "color": "Золотисто-янтарный",
            "grape": "Серсиаль, Вердельо, Альбильо",
            "description": hist.legend_summary,
            "features": {"sweetness": 2, "sparkling": False, "acidity": 3.8, "tannin": 1.5, "body": 4.6, "oak": True}
        }

    # 2.1 Проверка упоминания исторических вин в свободной фразе
    if "мадер" in s and ("массандр" in s or "крымск" in s):
        hist_m = HISTORICAL_WINES_DB.get("massandra-madera-krymskaya")
        if hist_m:
            for w in wines_list:
                if "мадер" in w["name"].lower():
                    return w
            return {
                "id": hist_m.wine_slug,
                "name": hist_m.wine_name,
                "winery": hist_m.founder,
                "category": "Крепленое",
                "color": "Золотисто-янтарный",
                "grape": "Серсиаль, Вердельо, Альбильо",
                "description": hist_m.legend_summary,
                "features": {"sweetness": 2, "sparkling": False, "acidity": 3.8, "tannin": 1.5, "body": 4.6, "oak": True}
            }
    if "портвейн" in s and ("ливади" in s or "массандр" in s):
        hist_p = HISTORICAL_WINES_DB.get("massandra-portveyn-krasnyy-livadiya")
        if hist_p:
            for w in wines_list:
                if "портвейн" in w["name"].lower() or "ливадия" in w["name"].lower():
                    return w
            return {
                "id": hist_p.wine_slug,
                "name": hist_p.wine_name,
                "winery": hist_p.founder,
                "category": "Крепленое",
                "color": "Красное",
                "grape": "Каберне Совиньон",
                "description": hist_p.legend_summary,
                "features": {"sweetness": 3, "sparkling": False, "acidity": 3.5, "tannin": 2.8, "body": 4.8, "oak": True}
            }

    # 3. Фильтрация токенов без стоп-слов
    all_tokens = [t for t in re.split(r"[^a-zA-Zа-яА-Я0-9]+", s) if len(t) >= 3 and not t.isdigit()]
    meaningful_tokens = [t for t in all_tokens if t not in STOP_WORDS and len(t) >= 4]

    # Если есть значимые слова (например, "шато", "талю", "каберне")
    search_tokens = meaningful_tokens if meaningful_tokens else all_tokens

    if search_tokens:
        # Ищем строгое вхождение всех значимых токенов
        for w in wines_list:
            w_str = (w.get("id", "") + " " + w.get("name", "") + " " + w.get("winery", "")).lower()
            if all(tok in w_str for tok in search_tokens):
                return w

        # Если не найдено, ищем хотя бы 2 совпадения или по первому ключевому
        if len(search_tokens) >= 2:
            for w in wines_list:
                w_str = (w.get("id", "") + " " + w.get("name", "")).lower()
                matches = sum(1 for tok in search_tokens if tok in w_str)
                if matches >= 2:
                    return w

    # Поиск прямого вхождения подстроки
    for w in wines_list:
        w_name_low = w.get("name", "").lower()
        if w_name_low and (w_name_low in s or (len(s) > 5 and s in w_name_low)):
            return w

    return None


# -----------------------------------------------------------------------------
# 3. Гастрономический ответ: Вино -> Блюда (Wine -> Food Pairing)
# -----------------------------------------------------------------------------

def render_food_pairing_answer(wine: dict, wine_slug: str = "", lang: str = "ru") -> str:
    """
    Формирует лаконичный, аргументированный и ясный ответ на вопрос «К какому блюду подходит это вино?»:
    - Кухня и несколько конкретных блюд
    - Заголовок: Почему подходит (на русском или английском)
    - Аргументы: химия вкуса, выдержка, подача
    """
    hist = HISTORICAL_WINES_DB.get(wine_slug) if wine_slug else None
    if hist and len(hist.wine_name) > len(wine.get("name", "")):
        raw_name = hist.wine_name
    else:
        raw_name = wine.get("name", "выбранное вино")

    is_en = (lang == "en")
    if is_en:
        try:
            from sommelier.i18n import translate_wine_name
            name = translate_wine_name(raw_name, "en")
        except Exception:
            name = raw_name
    else:
        name = raw_name

    color = (wine.get("color") or wine.get("category") or "").lower()
    cat = (wine.get("category") or "").lower()
    grape = (wine.get("grape") or "").lower()
    desc = (wine.get("description") or "").lower()
    wine_type = (wine.get("type") or "").lower()
    features = wine.get("features") or {}

    all_text = f"{raw_name} {color} {cat} {grape} {desc} {wine_type} {wine_slug}".lower()

    is_fortified = (
        "мадер" in all_text or "портвейн" in all_text or "херес" in all_text or
        "madera" in all_text or "portveyn" in all_text or "heres" in all_text or
        "креплен" in all_text or "десертн" in all_text or "ликерн" in all_text
    )
    is_sparkling = (
        features.get("sparkling", False) or "игрист" in all_text or "брют" in all_text or
        "brut" in all_text or "шампан" in all_text or "просекко" in all_text
    )
    
    acidity = float(features.get("acidity") or 3.8)
    tannins = float(features.get("tannin") or 2.5)
    body = float(features.get("body") or 3.2)
    has_oak = bool(
        features.get("oak") or "бочк" in desc or "дуб" in desc or "ванил" in desc or "выдержк" in desc
    )

    is_white = (
        "бел" in cat or "бел" in color or "white" in cat or "белое" in wine_type or
        any(c in color for c in ["золотист", "соломенн", "янтарн", "желт"]) or
        any(g in grape for g in ["шардоне", "совиньон", "рислинг", "алиготе", "пино блан", "пино гри", "ркацители", "мускат"])
    )
    is_rose = "розов" in cat or "розов" in color or "rose" in cat or "розе" in all_text or "лососев" in color
    is_red = (
        "красн" in cat or "красн" in color or "red" in cat or "красное" in wine_type or
        any(c in color for c in ["рубин", "гранат", "вишнев", "бордо"]) or
        any(g in grape for g in ["каберне", "саперави", "мерло", "красностоп", "шираз", "сира", "пино нуар", "бастардо", "мальбек"])
    )

    is_bold_red = is_red and (
        tannins >= 2.8 or any(g in grape or g in all_text for g in [
            "красностоп", "каберне", "саперави", "шираз", "сира", "мальбек", "мурведр", "бастардо", "цимлянск"
        ])
    )

    lines: List[str] = []

    if is_en:
        lines.append(f"### Gastronomic Pairings for «{name}»\n")
        lines.append("**Cuisine & Ideal Dishes:**")
    else:
        lines.append(f"### Гастрономические сочетания для вина «{name}»\n")
        lines.append("**Кухня и идеальные блюда:**")

    if is_fortified and ("мадер" in all_text or "madera" in all_text):
        if is_en:
            lines.append("• **French & European Classics:** Rich French onion soup with gruyère toast, tender duck liver pâté on warm brioche with figs.")
            lines.append("• **Mediterranean Cheese Board:** Aged Parmesan, Gruyère, or Manchego with walnuts and olives.")
            lines.append("• **Savory Gastronomy:** Roasted game poultry with wild mushrooms, hot-smoked halibut or eel.")
            lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
            lines.append(f"• **Cutting Dense Fats (High Alcohol + Acidity):** Noble fortification (19% ABV) combined with vibrant natural acidity ({acidity:.1f}/5) acts as an instant palate cleanser: it effortlessly dissolves the heavy fats of aged cheeses and rich pâtés without lingering heaviness.")
            lines.append("• **Maderization & Roasted Nut Bouquet:** Extended oxidative aging in warm solar oak barrels creates deep aromas of roasted hazelnuts, caramel, and toasted rye crust, which resonate seamlessly with caramelized onions and roasted fowl.")
            lines.append("• **Umami & Salt Contrast:** The salt in mature hard cheeses and the savory umami of sautéed wild mushrooms soften the alcohol heat and highlight the wine's dried fruit and vanilla facets.")
            lines.append("• **Serving (14–16 °C):** Slightly chilled in a tulip glass to soften alcohol warmth while focusing the rich nutty bouquet.")
        else:
            lines.append("• **Французская и европейская классика:** густой луковый суп с гренкой под расплавленным сыром Грюйер, нежный утиный паштет на теплой бриоши с инжиром.")
            lines.append("• **Средиземноморская сырная тарелка:** выдержанный Пармезан или Грюйер с колотым грецким орехом и оливками.")
            lines.append("• **Русская и авторская:** запеченная птица с лесными грибами, палтус или угорь горячего копчения.")
            lines.append("\n**Почему подходит (гастрономические причины):**")
            lines.append(f"• **Расщепление тяжелых жиров (крепость + кислотность):** благородная крепость (19%) в сочетании с высокой природной кислотностью ({acidity:.1f}/5) работает как идеальный очиститель рецепторов: мгновенно растворяет плотный жир сыров и паштетов, не оставляя тяжести на нёбе.")
            lines.append("• **Мадеризация и ореховый тон:** длительное созревание в дубовых бочках на солнце рождает глубокий аромат каленого ореха, карамели и корочки ржаного хлеба, который безупречно резонирует с карамелизованным луком и аппетитной корочкой запеченной птицы.")
            lines.append("• **Контраст умами и соли:** соль зрелого твердого сыра и вкус жареных лесных грибов смягчают алкоголь и выводят на первый план сухофруктово-ванильные грани вина.")
            lines.append("• **Подача (14–16 °C):** прохладная подача в тюльпановидном бокале сглаживает спиртуозность и концентрирует ореховый букет.")

    elif is_fortified and ("портвейн" in all_text or "portveyn" in all_text):
        if is_en:
            lines.append("• **European Desserts:** Premium dark chocolate (75–85%), warm chocolate fondant with cherries, pecan or walnut tart with salted caramel.")
            lines.append("• **Cheese Classics (Flavor Contrast):** Piquant noble blue cheeses (Gorgonzola Piccante, Roquefort, Stilton).")
            lines.append("• **Savory Meat Gastronomy:** Duck pâté with lingonberry confit, seared beef steak with creamy blue cheese glaze.")
            lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
            lines.append(f"• **Synergy of Salt & Natural Sweetness:** Velvety tannins ({tannins:.1f}/5) and deep liqueur sweetness form a textbook contrast with salty blue cheeses: cheese salinity tames the wine's sweet richness, while the wine instantly smooths out pungent mold bitterness.")
            lines.append("• **Weight & Textural Harmony:** The warming, full-bodied profile coats the palate and holds its ground against bittersweet cocoa, toasted nuts, and dark berry glazes without being overpowered.")
            lines.append("• **Oak Barrel Aging:** Extended barrel aging yields nuanced notes of prune in chocolate, Morocco leather, dried cherry, and sun-dried fig, ensuring a continuous chocolate-berry finish.")
            lines.append("• **Serving (16–18 °C):** Served slightly below room temperature in a digestif glass to emphasize velvet smoothness.")
        else:
            lines.append("• **Европейская десертная:** премиальный горький шоколад (75–85%), шоколадный фондан с вишней, ореховые тарты с карамелью.")
            lines.append("• **Сырная классика (контраст вкусов):** пикантные сыры с благородной голубой плесенью (Горгонзола Пиканте, Рокфор, Стилтон).")
            lines.append("• **Мясная гастрономия:** утиный паштет с брусничным конфитюром, сочный стейк с соусом из голубого сыра.")
            lines.append("\n**Почему подходит (гастрономические причины):**")
            lines.append(f"• **Синергия соли и природной сладости:** бархатные танины ({tannins:.1f}/5) и густая ликерная сладость портвейна вступают в гармоничный контраст с солеными голубыми сырами: соль сыра гасит избыток сладости вина, а вино мгновенно сглаживает острую плесневую горечь.")
            lines.append("• **Плотность и богатство текстуры:** полнотелое согревающее вино обволакивает рецепторы и звучит на равных с насыщенными десертами и пряными соусами, не теряясь за ними.")
            lines.append("• **Выдержка в дубе:** тона чернослива в шоколаде, сафьяна, сушеной вишни и вяленого инжира создают непрерывное шоколадно-ягодное послевкусие.")
            lines.append("• **Подача (16–18 °C):** подается чуть ниже комнатной температуры в дижестивном бокале, чтобы подчеркнуть бархатистость.")

    elif is_sparkling:
        if is_en:
            lines.append("• **Seafood & Raw Bar:** Fresh oysters with a squeeze of lemon, wild salmon or tuna ceviche, grilled tiger prawns with garlic herbs.")
            lines.append("• **Celebration Classics:** Red caviar canapés on crisp brioche or toasted baguette with sweet-cream butter.")
            lines.append("• **European Light Fare:** Baked Camembert or Brie with fresh rosemary and berries, thinly sliced prosciutto with figs.")
            lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
            lines.append(f"• **Palate Cleansing via Effervescence (Perlage):** Millions of delicate carbon dioxide bubbles paired with vibrant acidity ({acidity:.1f}/5) mechanically and chemically wipe away oily films from caviar, butter, and seafood, restoring crisp freshness before every bite.")
            lines.append("• **Salinity vs. Fresh Citrus Contrast:** Gentle marine salinity against crunchy citrus acidity creates an expansive gastronomic lift.")
            lines.append("• **Autolytic Yeast Notes:** Traditional lees aging provides aromas of freshly baked croissant and brioche that echo crusty bread and creamy cheeses.")
            lines.append("• **Serving (6–8 °C):** Crisp chilling preserves fine bubbling and delivers a crystal-pure first sip.")
        else:
            lines.append("• **Средиземноморская и морская:** свежие устрицы с каплей лимона, севиче из дикого лосося или тунца, жареные тигровые креветки на гриле.")
            lines.append("• **Праздничная русская:** бутерброды с красной икрой на хрустящих тостах со сливочным маслом.")
            lines.append("• **Европейская легкая:** запеченный сыр Камамбер или Бри с розмарином и ягодами, тонко нарезанное прошутто с инжиром.")
            lines.append("\n**Почему подходит (гастрономические причины):**")
            lines.append(f"• **Очищение рецепторов пузырьками (перляж):** миллионы углекислых пузырьков в паре с высокой кислотностью ({acidity:.1f}/5) механически и химически сметают маслянистую пленку икры, сливочного масла и морепродуктов, возвращая абсолютную свежесть нёбу перед каждым новым кусочком.")
            lines.append("• **Контраст соленого и свежего:** нежная солоноватость даров моря на фоне хрустящей цитрусовой свежести вина рождает богатый гастрономический объем.")
            lines.append("• **Дрожжевая выдержка:** традиционная выдержка на осадке придает вину аппетитные тона свежеиспеченного круассана и поджаренной бриоши, которые идеально рифмуются с хрустящим багетом и мягкими сырами.")
            lines.append("• **Подача (6–8 °C):** бодрящий холод удерживает тонкую игру пузырьков и делает первый глоток кристально чистым.")

    elif is_bold_red:
        body_disp = max(body, 3.8)
        if is_en:
            lines.append("• **Charcoal Grilled Steaks:** Juicy marbled Ribeye or Striploin steak cooked medium over charcoal with rosemary and garlic butter.")
            lines.append("• **Slow-Cooked Braised Meats:** Braised beef shank in rich demi-glace, venison or wild boar stew with juniper berries.")
            lines.append("• **Aged Hard Cheeses:** Mature Cheddar, aged Parmesan, or 12+ month farmhouse Gouda.")
            lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
            lines.append(f"• **Tannin-Protein Binding:** Pronounced grape skin tannins ({max(tannins, 3.8):.1f}/5) chemically bind to meat proteins and fats. The meat feels noticeably more tender, while rich steak fats completely neutralize wine astringency, making the wine taste remarkably juicy and velvety.")
            lines.append(f"• **Weight Matching (Wine vs. Dish Power):** A dense, full body ({body_disp:.1f}/5) matches the intensity of smoke, rendered beef fat, and savory spices without fading into the background.")
            lines.append(f"• **Acidity Cleansing:** Fresh acidity ({acidity:.1f}/5) cuts through dense animal fat, keeping the entire meal refreshing and digestible.")
            lines.append("• **Wood-Spice Synergy:** Oak aging brings notes of black pepper, cedar, vanilla, and roasted cacao that amplify the charred steak crust.")
            lines.append("• **Serving (16–18 °C):** Cool cellar temperature in an ample Bordeaux glass. Warmth reveals alcohol fumes, while over-chilling makes tannins harsh.")
        else:
            lines.append("• **Мясной гриль и кавказская кухня:** сочный мраморный стейк Рибай или Стриплойн средней прожарки (Medium) на углях с чесночным маслом и розмарином.")
            lines.append("• **Сытные мясные блюда:** томленая говяжья голяшка в соусе демигляс, жаркое из дичи или оленины с можжевеловыми ягодами.")
            lines.append("• **Выдержанные сыры:** Чеддер, твердый пармезан или фермерская Гауда от 12 месяцев созревания.")
            lines.append("\n**Почему подходит (гастрономические причины):**")
            lines.append(f"• **Связывание танинов с белком мяса:** выраженные танины ({max(tannins, 3.8):.1f}/5) — природные дубильные вещества из кожицы ягод — связываются с волокнами и белком сочного мяса. Мясо становится нежнее, а жир и сок стейка полностью нейтрализуют вяжущую терпкость вина — вино ощущается шелковистым, сочным и ягодным.")
            lines.append(f"• **Соответствие по мощности (вес вина и блюда):** плотное и мощное тело ({body_disp:.1f}/5) выдерживает напор насыщенного мясного сока и дымных специй, не теряясь на их фоне.")
            lines.append(f"• **Очищение рецепторов кислотностью:** живая кислотность ({acidity:.1f}/5) растворяет тяжелый животный жир, не давая трапезе казаться приторной или утомительной.")
            lines.append("• **Древесно-пряная синергия:** выдержка в дубовых бочках обогащает букет нотами черного перца, кедра, ванили и табака, которые усиливают аромат запеченной на огне мясной корочки.")
            lines.append("• **Подача (16–18 °C):** легкая комнатная прохлада в объемном бокале «Бордо». В тепле вино спиртуозно, а при переохлаждении танины становятся жесткими и горькими.")

    elif is_red:
        if is_en:
            lines.append("• **French & European Fare:** Roasted duck breast with cherry or lingonberry reduction, wild mushroom tagliatelle with black truffle oil.")
            lines.append("• **Tender Poultry & Meats:** Slow-braised rabbit in white wine and herbs, roast turkey roll with prunes.")
            lines.append("• **Soft Blooming Cheeses:** Brie de Meaux, Camembert, soft alpine cheeses.")
            lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
            lines.append(f"• **Silky Delicate Tannins:** Soft tannin structure ({tannins:.1f}/5) never overpowers the delicate flavor of poultry or braised rabbit and leaves the palate supple.")
            lines.append(f"• **Cutting Poultry Fat:** Lively berry acidity ({acidity:.1f}/5) mimics a natural tart berry sauce, cutting through rich duck fat.")
            lines.append("• **Earthy Forest Notes:** Ripe cherry, raspberry, forest floor, and baking spice notes harmonize with earthiness of wild mushrooms.")
            lines.append("• **Serving (14–16 °C):** Lightly chilled in a wide Burgundy bowl to release layered floral and berry aromas.")
        else:
            lines.append("• **Французская и европейская кухня:** запеченная утиная грудка с брусничным или вишневым соусом, паста с лесными грибами и трюфельным маслом.")
            lines.append("• **Нежное мясо:** томленый кролик в белом вине с прованскими травами, сочный рулет из индейки с черносливом.")
            lines.append("• **Мягкие сыры:** Бри, Камамбер с белой плесенью, мягкие фермерские сыры.")
            lines.append("\n**Почему подходит (гастрономические причины):**")
            lines.append(f"• **Шелковистые деликатные танины:** мягкая танинная структура ({tannins:.1f}/5) не глушит тонкий деликатный вкус птицы и кролика, не пересушивая нёбо.")
            lines.append(f"• **Баланс подкожного утиного жира:** яркая ягодная кислотность ({acidity:.1f}/5) работает как натуральный ягодный соус: она рассекает жирность утки и делает блюдо легким и питким.")
            lines.append("• **Лесная органолептика:** оттенки спелой вишни, малины, лесного подлеска и пряностей идеально гармонируют с землистым вкусом грибов и трав.")
            lines.append("• **Подача (14–16 °C):** слегка охлажденным в широком бокале формы «Бургундия» для максимального раскрытия тонких ароматов.")

    elif is_white:
        if has_oak or body >= 3.3 or "шардоне" in grape or "chardonnay" in grape:
            body_disp = max(body, 3.5)
            if is_en:
                lines.append("• **Seafood & Butter Sauces:** Pan-seared sea scallops in garlic herb butter, grilled salmon steak with creamy caviar sauce.")
                lines.append("• **Italian Classics:** Creamy pasta Carbonara, wild porcini risotto with aged parmesan.")
                lines.append("• **Poultry & White Meat:** Farmhouse chicken in creamy Dijon mustard sauce, roast turkey breast.")
                lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
                lines.append(f"• **Creamy Density & Palate Weight:** Oak maturation and malolactic fermentation create a rounded body ({body_disp:.1f}/5) that perfectly matches the weight of butter sauces, cream, and tender poultry.")
                lines.append(f"• **Citrus Acidity Cleansing:** Vibrant yet integrated acidity ({acidity:.1f}/5) cuts through heavy dairy and seafood fats, renewing taste clarity.")
                lines.append("• **Toasted Oak Notes:** Nuances of vanilla, brioche, ripe peach, and roasted hazelnuts mirror grilled poultry crusts and cheese richness.")
                lines.append("• **Serving (10–12 °C):** Moderately cool in a wide Chardonnay glass to avoid muting butter and vanilla complexity.")
            else:
                lines.append("• **Североморская и французская:** морские гребешки на сливочном масле с чесноком, стейк из лосося или форели в сливочно-икорном соусе.")
                lines.append("• **Итальянская классика:** сливочная паста Карбонара, ризотто с белыми грибами и пармезаном.")
                lines.append("• **Птица и белое мясо:** фермерский цыпленок в сливочно-горчичном соусе или запеченная индейка с пряными травами.")
                lines.append("\n**Почему подходит (гастрономические причины):**")
                lines.append(f"• **Сливочная плотность и текстура:** благодаря выдержке в дубе и кремовой структуре тело вина ({body_disp:.1f}/5) идеально совпадает по «весу» со сливочным маслом, соусами и сочным филе птицы — вино не теряется на фоне сытных горячих блюд, а мягко и округло обволакивает нёбо.")
                lines.append(f"• **Очищение рецепторов кислотностью:** живая, но деликатная кислотность ({acidity:.1f}/5) действует как легкий цитрусовый акцент: она рассекает плотную маслянистую пленку соусов и жирной рыбы, обновляя вкусовую чувствительность перед каждым следующим кусочком.")
                lines.append("• **Ароматический резонанс с корочкой:** благородные ванильно-древесные тона бочки, ноты спелого персика, нектарина и поджаренных тостов перекликаются с золотистой корочкой гриля и ореховыми нотами сыров.")
                lines.append("• **Подача (10–12 °C):** подается умеренно прохладным в широком бокале для Шардоне: ледяная температура зажала бы богатые ванильно-сливочные оттенки, а легкая прохлада раскрывает их полностью.")
        else:
            if is_en:
                lines.append("• **Grilled Mediterranean Fish:** Sea bass or sea bream over charcoal with sea salt and herbs, steamed mussels in white wine and garlic.")
                lines.append("• **Pan-Asian Freshness:** White fish ceviche, tuna sashimi with avocado and citrus ponzu, crisp tiger prawn salad.")
                lines.append("• **Young Fresh Cheeses:** Chèvre goat cheese, fresh Mozzarella di Bufala with ripe tomatoes and fresh basil.")
                lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
                lines.append(f"• **Fresh Lemon Squeeze Effect:** Snappy mineral acidity ({acidity:.1f}/5) performs the role of fresh lime or lemon juice: elevates sweet seafood protein and eliminates oily aftertastes.")
                lines.append(f"• **Crisp Light Body:** Lean, vibrant body ({body:.1f}/5) leaves a pristine feeling of lightness and energy.")
                lines.append("• **Herb & Citrus Palette:** Green apple, grapefruit, wet stone, and meadow herbs harmonize with fresh greens and extra virgin olive oil.")
                lines.append("• **Serving (8–10 °C):** Chilled to maintain crisp mineral tension and thirst-quenching bite.")
            else:
                lines.append("• **Средиземноморская рыба:** сибас или дорадо на гриле с морской солью и розмарином, свежие мидии в легком чесночном бульоне.")
                lines.append("• **Паназиатская свежесть:** севиче из белой рыбы, сашими с авокадо и цитрусовым соусом понзу, хрустящий салат с креветками.")
                lines.append("• **Молодые сыры:** козий сыр Шевр, нежная Моцарелла со спелыми томатами и свежим базиликом.")
                lines.append("\n**Почему подходит (гастрономические причины):**")
                lines.append(f"• **Эффект свежего лимона:** звонкая минеральная кислотность ({acidity:.1f}/5) работает как капля свежего сока лайма или лимона: подчеркивает природную сладость нежного белка рыбы и креветок, полностью устраняя маслянистый или специфический рыбный привкус.")
                lines.append(f"• **Легкость структуры:** тонкое и свежее тело ({body:.1f}/5) оставляет ощущение кристальной чистоты и легкости, не перегружая трапезу.")
                lines.append("• **Цитрусово-травянистая палитра:** чистые ноты зеленого яблока, грейпфрута, белых цветов и луговых трав идеально сочетаются со свежей зеленью и оливковым маслом.")
                lines.append("• **Подача (8–10 °C):** бодрящий холод удерживает хрустящую минеральную структуру вина и делает каждый глоток освежающим.")

    elif is_rose:
        if is_en:
            lines.append("• **Mediterranean Classics:** Provençal Salade Niçoise with seared tuna, seafood and chicken paella with saffron.")
            lines.append("• **Light Grill & Skewers:** Tiger prawn skewers with sweet smoked paprika, chicken kebab with fresh herbs.")
            lines.append("• **Antipasti & Cheeses:** Bruschetta with prosciutto and sun-dried tomatoes, fresh goat cheeses.")
            lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
            lines.append(f"• **Gastronomic Bridge:** Rosé marries the thirst-quenching acidity ({acidity:.1f}/5) of white wines with the subtle red-berry tannins ({tannins:.1f}/5) of reds, allowing it to seamlessly accompany both shellfish and poultry at the same table.")
            lines.append("• **Palate Cleansing:** Juicy red fruit acidity sweeps away vinaigrettes and oils, leaving a crisp berry impression.")
            lines.append("• **Serving (10–12 °C):** Sweet spot temperature preserving red berry brightness and crisp freshness.")
        else:
            lines.append("• **Средиземноморская классика:** провансальский салат Нисуаз со свежим тунцом и фасолью, паэлья с морепродуктами и кусочками цыпленка.")
            lines.append("• **Легкий гриль:** тигровые креветки на шпажках со сладкой паприкой, куриный шашлык с зеленью и овощами.")
            lines.append("• **Закуски и сыры:** брускетты с прошутто и вялеными томатами, молодые козьи сыры.")
            lines.append("\n**Почему подходит (гастрономические причины):**")
            lines.append(f"• **Универсальный гастрономический мост:** розе сочетает бодрящую освежающую кислотность ({acidity:.1f}/5) белого вина с легкими бархатистыми ягодными танинами ({tannins:.1f}/5) красного. Это позволяет ему уверенно сопровождать и морепродукты, и белое мясо одновременно.")
            lines.append(f"• **Очищение рецепторов:** сочная ягодная кислинка легко смывает маслянистость заправки салатов и соусов, оставляя свежее ягодное послевкусие.")
            lines.append("• **Подача (10–12 °C):** золотая середина температуры, сохраняющая ягодную сочность и свежесть.")

    else:
        if is_en:
            lines.append("• **European Charcuterie & Cheeses:** Farmhouse cheese board with walnuts and blossom honey, cured meats (prosciutto, duck ham).")
            lines.append("• **Main Courses:** Herb-roasted poultry, tender veal medallions, or grilled fish over coals.")
            lines.append("\n**Why it Pairs (Gastronomic Rationale):**")
            lines.append(f"• **Balanced Acidity & Fat Cleansing:** Harmonious acidity ({acidity:.1f}/5) acts as an effortless palate cleanser against rich cheese and roasted meats.")
            lines.append(f"• **Weight & Texture Harmony:** Balanced body ({body:.1f}/5) strikes an ideal balance, never overshadowing poultry while standing up to savory charcuterie.")
            lines.append("• **Flavor Synergy:** A structured dry profile highlights the natural quality of ingredients for a well-rounded dining ensemble.")
            lines.append("• **Serving (12–14 °C):** Cellar temperature ensuring a perfect equilibrium of aromatic bouquet and crisp freshness.")
        else:
            lines.append("• **Европейская классика:** фермерское сырное плато с грецкими орехами и цветочным медом, мясные деликатесы (прошутто, сыровяленая утиная грудка).")
            lines.append("• **Горячие блюда:** запеченное мясо птицы с прованскими травами, нежная телятина или сочная рыба на углях.")
            lines.append("\n**Почему подходит (гастрономические причины):**")
            lines.append(f"• **Баланс кислотности и жирности (очищение рецепторов):** сбалансированная кислотность вина ({acidity:.1f}/5) работает как естественный освежитель вкуса: она нейтрализует маслянистость сыров и запеченного мяса, не позволяя блюду казаться тяжелым.")
            lines.append(f"• **Соответствие по весу и плотности:** сбалансированная плотность тела ({body:.1f}/5) дает оптимальный гастрономический компромисс: вино не заглушает деликатный вкус птицы, но при этом уверенно держится рядом с насыщенными мясными закусками.")
            lines.append("• **Вкусовая гармония:** сухой структурированный профиль подчеркивает натуральный вкус качественных продуктов, создавая цельный и гармоничный дегустационный ансамбль.")
            lines.append("• **Подача (12–14 °C):** универсальная температура погреба, сохраняющая идеальный баланс между свежестью и выразительностью аромата.")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# 4. Вкусовой профиль вина (Опиши вкус, кислотность и танины)
# -----------------------------------------------------------------------------

def render_taste_profile_answer(wine: dict, wine_slug: str = "", lang: str = "ru") -> str:
    """Формирует структурированное дегустационное описание вкуса, кислотности и танинов."""
    hist = HISTORICAL_WINES_DB.get(wine_slug) if wine_slug else None
    if hist and len(hist.wine_name) > len(wine.get("name", "")):
        raw_name = hist.wine_name
    else:
        raw_name = wine.get("name", "выбранное вино")

    is_en = (lang == "en")
    if is_en:
        try:
            from sommelier.i18n import translate_wine_name, translate_wine_description
            name = translate_wine_name(raw_name, "en")
        except Exception:
            name = raw_name
    else:
        name = raw_name

    color = (wine.get("color") or wine.get("category") or "").lower()
    features = wine.get("features") or {}
    desc = wine.get("description") or ""

    acidity = float(features.get("acidity") or 3.8)
    tannins = float(features.get("tannin") or 2.5)
    body = float(features.get("body") or 3.8)
    sweetness_code = features.get("sweetness") or 0
    sweetness_map_ru = {0: "Сухое (до 4 г/л сахара)", 1: "Полусухое (4–18 г/л)", 2: "Полусладкое (18–45 г/л)", 3: "Сладкое / Десертное (от 45 г/л)"}
    sweetness_map_en = {0: "Dry (up to 4 g/l residual sugar)", 1: "Off-Dry (4–18 g/l)", 2: "Semi-Sweet (18–45 g/l)", 3: "Sweet / Dessert (45+ g/l)"}
    sweetness_desc = sweetness_map_en.get(sweetness_code, "Dry") if is_en else sweetness_map_ru.get(sweetness_code, "Сухое")

    if is_en:
        acid_word = "Mild, soft" if acidity < 3.2 else ("Balanced, vibrant" if acidity <= 4.0 else "Crisp, racy")
        tannin_word = "Silky, delicate" if tannins < 2.5 else ("Noticeable, velvety" if tannins <= 3.8 else "Bold, structured")
        body_word = "Light, refreshing" if body < 3.0 else ("Medium-bodied, harmonious" if body <= 4.0 else "Full-bodied, deep")
    else:
        acid_word = "Умеренная, мягкая" if acidity < 3.2 else ("Сбалансированная, живая" if acidity <= 4.0 else "Яркая, бодрящая")
        tannin_word = "Шелковистые, деликатные" if tannins < 2.5 else ("Ощутимые, бархатистые" if tannins <= 3.8 else "Мощные, структурные")
        body_word = "Легкое, освежающее" if body < 3.0 else ("Среднетелое, гармоничное" if body <= 4.0 else "Полнотелое, глубокое")

    aromas = features.get("aroma") or []
    if is_en:
        aroma_map = {
            "вишня": "ripe cherry", "черешня": "dark cherry", "чернослив": "prune", "слива": "plum",
            "ежевика": "blackberry", "черная смородина": "blackcurrant", "малина": "raspberry",
            "клубника": "strawberry", "ягоды": "wild berries", "ваниль": "sweet vanilla",
            "шоколад": "dark chocolate", "дуб": "toasted oak", "табак": "cigar tobacco",
            "кожа": "fine leather", "специи": "baking spices", "перец": "black pepper",
            "зеленое яблоко": "green apple", "груша": "crisp pear", "персик": "white peach",
            "абрикос": "apricot", "цитрусовые": "citrus zest", "лимон": "lemon",
            "лайм": "lime", "грейпфрут": "grapefruit", "белые цветы": "white blossom",
            "травы": "meadow herbs", "минералы": "crushed stone minerals", "мед": "wildflower honey",
            "бриошь": "toasted brioche", "сливочное масло": "sweet cream butter"
        }
        translated_aromas = [aroma_map.get(a.lower(), a) for a in aromas]
        aroma_str = ", ".join(translated_aromas) if translated_aromas else "dark berries, forest herbs, fruit nuances"
    else:
        aroma_str = ", ".join(aromas) if aromas else "ягоды, полевые травы, фруктовые оттенки"

    if is_en:
        lines = [
            f"### Taste Profile for «{name}»\n",
            "**Structure & Taste Balance:**",
            f"• **Acidity:** {acidity:.1f} of 5 — {acid_word}.",
            f"• **Tannins:** {tannins:.1f} of 5 — {tannin_word}.",
            f"• **Body / Density:** {body:.1f} of 5 — {body_word}.",
            f"• **Sweetness:** {sweetness_desc}.",
            "\n**Aromatic Bouquet & Palette:**",
            f"In the glass notes emerge of: {aroma_str}.",
        ]
        if desc.strip():
            try:
                from sommelier.i18n import translate_wine_description
                clean_desc = translate_wine_description(desc[:300].strip().rstrip(".") + ".", None, "en")
            except Exception:
                clean_desc = desc[:300].strip().rstrip(".") + "."
            lines.append(f"\n**Tasting Note:**\n«{clean_desc}»")
        serve_temp = "16–18" if ("красн" in color or "red" in color) else ("8–10" if "игрист" in raw_name.lower() or "sparkling" in raw_name.lower() else "10–12")
        lines.append(f"\n**Recommended Serving Temperature:** {serve_temp} °C.")
    else:
        lines = [
            f"### Вкусовой профиль вина «{name}»\n",
            "**Структура и баланс вкуса:**",
            f"• **Кислотность:** {acidity:.1f} из 5 — {acid_word}.",
            f"• **Танинность:** {tannins:.1f} из 5 — {tannin_word}.",
            f"• **Тело / Плотность:** {body:.1f} из 5 — {body_word}.",
            f"• **Сладость:** {sweetness_desc}.",
            "\n**Ароматический букет и палитра:**",
            f"В бокале раскрываются ноты: {aroma_str}.",
        ]
        if desc.strip():
            clean_desc = desc[:300].strip().rstrip(".") + "."
            lines.append(f"\n**Дегустационная заметка:**\n«{clean_desc}»")
        serve_temp = "16–18" if "красн" in color else ("8–10" if "игрист" in raw_name.lower() else "10–12")
        lines.append(f"\n**Рекомендуемая температура подачи:** {serve_temp} °C.")
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# 5. Подбор аналогов в каталоге (Подбери 3 похожих российских вина)
# -----------------------------------------------------------------------------

def find_analogs_in_catalog(wine: dict, wines_list: list, top_k: int = 3) -> list:
    """Подбирает ближайшие по стилю, цвету, сахару и телу российские вина из каталога."""
    w_id = wine.get("id")
    w_name = (wine.get("name") or "").lower()
    w_cat = (wine.get("category") or wine.get("color") or "").lower()
    w_feat = wine.get("features") or {}
    w_sweet = w_feat.get("sweetness")
    w_sparkling = bool(w_feat.get("sparkling"))
    w_grapes = set(re.findall(r"\w{4,}", (wine.get("grape") or "").lower()))
    w_oak = bool(w_feat.get("oak"))

    is_fort = "мадер" in w_name or "портвейн" in w_name or "херес" in w_name or "креплен" in w_cat or "десертн" in w_cat

    candidates = []
    for cand in wines_list:
        c_id = cand.get("id")
        c_name = (cand.get("name") or "").lower()
        if c_id == w_id or (c_name and c_name == w_name):
            continue
        c_feat = cand.get("features") or {}
        c_cat = (cand.get("category") or cand.get("color") or "").lower()
        c_sparkling = bool(c_feat.get("sparkling"))
        
        # Фильтр по типу игристости
        if c_sparkling != w_sparkling:
            continue

        score = 0.50
        reasons = []

        is_c_fort = "мадер" in c_name or "портвейн" in c_name or "херес" in c_name or "ликерн" in c_cat or "креплен" in c_cat or "десертн" in c_cat

        if is_fort:
            if is_c_fort:
                score += 0.35
                reasons.append("Традиционный южный стиль крепленого десертного вина")
            else:
                continue
        else:
            if is_c_fort:
                continue

        # Категория / цвет
        if c_cat and w_cat and (c_cat in w_cat or w_cat in c_cat):
            score += 0.20
            reasons.append("Одинаковая категория и цветовая гамма")

        # Сладость
        c_sweet = c_feat.get("sweetness")
        if w_sweet is not None and c_sweet is not None:
            if c_sweet == w_sweet:
                score += 0.15
                reasons.append("Точное совпадение по уровню сахара")
            elif abs(c_sweet - w_sweet) == 1:
                score += 0.05

        # Сортовой состав
        c_grapes = set(re.findall(r"\w{4,}", (cand.get("grape") or "").lower()))
        common_grapes = w_grapes & c_grapes
        if common_grapes:
            score += 0.15
            reasons.append("Схожий сортовой состав")

        # Выдержка в дубе
        c_oak = bool(c_feat.get("oak"))
        if c_oak and w_oak:
            score += 0.05
            reasons.append("Выдержка в дубовых бочках")

        norm_score = min(0.96, round(score, 2))
        candidates.append({
            "id": c_id,
            "name": cand.get("name"),
            "winery": cand.get("winery") or "Российская винодельня",
            "score": norm_score,
            "reasons": reasons,
            "facts": f"{cand.get('region') or 'Россия'}, сорт: {cand.get('grape') or 'автохтон'}",
            "image_url": cand.get("image_url") or f"/api/image/{c_id}"
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:top_k]


def render_analogs_answer(wine: dict, alternatives: list, lang: str = "ru") -> Tuple[str, list]:
    """Формирует понятный текст и карточки вин-аналогов из российского каталога."""
    hist = HISTORICAL_WINES_DB.get(wine.get("id")) if wine.get("id") else None
    raw_name = hist.wine_name if (hist and len(hist.wine_name) > len(wine.get("name", ""))) else wine.get("name", "выбранное вино")
    is_en = (lang == "en")

    if is_en:
        try:
            from sommelier.i18n import translate_wine_name, translate_winery, _translate_fact_line_en
            name = translate_wine_name(raw_name, "en")
        except Exception:
            name = raw_name
    else:
        name = raw_name

    if not alternatives:
        if is_en:
            text = f"No direct twins found for «{name}» in the current catalog slice. We recommend exploring indigenous Russian wines of matching color and sweetness."
        else:
            text = f"К вину «{name}» в текущем срезе каталога прямых близнецов не найдено. Рекомендуем обратить внимание на автохтонные российские позиции того же цвета и сладости."
        return text, []

    if is_en:
        lines = [
            f"### Russian Analogs for «{name}»\n",
            f"Selected {len(alternatives)} Russian wines with close style and flavor balance from the catalog:\n"
        ]
    else:
        lines = [
            f"### Российские аналоги к вину «{name}»\n",
            f"Подобрал {len(alternatives)} близких по стилю и вкусовому балансу российских вин из каталога:\n"
        ]

    picks = []
    for i, a in enumerate(alternatives, 1):
        raw_p_name = a.get("name") or "Российское вино"
        raw_winery = a.get("winery") or ""
        raw_facts = a.get("facts") or ""
        score = a.get("score") or 0.85
        score_pct = int(score * 100) if score <= 1.0 else int(score)
        reasons = a.get("reasons") or []

        if is_en:
            try:
                from sommelier.i18n import translate_wine_name, translate_winery, _translate_fact_line_en
                p_name = translate_wine_name(raw_p_name, "en")
                winery = translate_winery(raw_winery, "en")
                facts = _translate_fact_line_en(raw_facts)
            except Exception:
                p_name = raw_p_name
                winery = raw_winery
                facts = raw_facts
            reason_txt = "Similar grape varieties, regional style and acid balance"
            lines.append(f"**{i}. {p_name}** ({winery}) — similarity {score_pct}%")
            lines.append(f"   • {reason_txt}.")
            role_txt = "Close Analog"
        else:
            p_name = raw_p_name
            winery = raw_winery
            facts = raw_facts
            reason_txt = "; ".join(reasons[:2]) if reasons else "Схожий сортовой состав и баланс кислотности"
            lines.append(f"**{i}. {p_name}** ({winery}) — сходство {score_pct}%")
            lines.append(f"   • {reason_txt}.")
            role_txt = "Близкий аналог"

        picks.append({
            "id": a.get("id"),
            "name": p_name,
            "winery": winery,
            "score": score_pct,
            "role": role_txt,
            "facts": facts,
            "quote": reason_txt,
            "image_url": a.get("image_url") or f"/api/image/{a.get('id')}"
        })

    return "\n".join(lines), picks
