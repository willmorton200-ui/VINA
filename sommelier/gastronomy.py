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
    """Определяет вопрос о гастропарах / блюдах / еде / кухне к вину."""
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
        r"что приготовить"
    ]
    for p in patterns:
        if re.search(p, t):
            return True
    return False


def is_taste_profile_query(text: str) -> bool:
    """Определяет вопрос о вкусе / кислотности / танинах / ароматике вина."""
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
        r"дегустационн"
    ]
    for p in patterns:
        if re.search(p, t):
            return True
    return False


def is_analogs_query(text: str) -> bool:
    """Определяет запрос на поиск похожих вин / аналогов."""
    t = text.lower().strip()
    patterns = [
        r"аналог",
        r"похож.*вин",
        r"что похоже",
        r"альтернатив",
        r"замен.*этом",
        r"похожие по вкусу",
        r"найти похож"
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

def render_food_pairing_answer(wine: dict, wine_slug: str = "") -> str:
    """
    Формирует лаконичный, аргументированный и ясный ответ на вопрос «К какому блюду подходит это вино?»:
    - Кухня и несколько конкретных блюд
    - Заголовок: Почему подходит
    - Аргументы: химия вкуса, выдержка, подача
    """
    hist = HISTORICAL_WINES_DB.get(wine_slug) if wine_slug else None
    if hist and len(hist.wine_name) > len(wine.get("name", "")):
        name = hist.wine_name
    else:
        name = wine.get("name", "выбранное вино")
    color = (wine.get("color") or wine.get("category") or "").lower()
    cat = (wine.get("category") or "").lower()
    grape = (wine.get("grape") or "").lower()
    desc = (wine.get("description") or "").lower()
    features = wine.get("features") or {}

    is_fortified = (
        "мадер" in name.lower() or "портвейн" in name.lower() or "херес" in name.lower() or
        "madera" in wine_slug.lower() or "portveyn" in wine_slug.lower() or "heres" in wine_slug.lower() or
        "креплен" in cat or "десертн" in cat
    )
    is_sparkling = features.get("sparkling", False) or "игрист" in name.lower() or "брют" in name.lower() or "brut" in name.lower()
    
    acidity = float(features.get("acidity") or 3.8)
    tannins = float(features.get("tannin") or 2.5)
    body = float(features.get("body") or 3.8)
    sweetness_val = float(features.get("sweetness") or 1.0)
    has_oak = bool(features.get("oak") or "бочк" in desc or "дуб" in desc)

    is_bold_red = ("красн" in color) and (
        tannins >= 2.8 or any(g in grape or g in name.lower() for g in [
            "красностоп", "каберне", "саперави", "шираз", "сира", "мальбек", "мурведр", "бастардо", "цимлянск"
        ])
    )

    lines: List[str] = []
    lines.append(f"### Гастрономические сочетания для вина «{name}»\n")
    lines.append("**Кухня и идеальные блюда:**")

    if is_fortified and ("мадер" in name.lower() or "madera" in wine_slug.lower()):
        lines.append("• **Французская и европейская классика:** густой луковый суп с гренкой под расплавленным Грюйером, утиный паштет на бриоши с инжиром.")
        lines.append("• **Средиземноморская сырная тарелка:** выдержанный Пармезан или Грюйер с колотым грецким орехом и оливками.")
        lines.append("• **Русская и авторская:** запеченная птица с лесными грибами, палтус или угорь горячего копчения.")
        lines.append("\n**Почему подходит:**")
        lines.append(f"• **Химия вкуса:** высокая кислотность ({acidity:.1f}/5) и благородная крепость (19%) легко расщепляют животные жиры сыров и паштетов, очищая рецепторы. Соленость кристаллического сыра и умами жареных грибов смягчают алкоголь и высвобождают фруктово-ванильные грани вина.")
        lines.append("• **Выдержка и мадеризация:** созревание в дубовых бочках на открытых солнечных площадках рождает каленый орехово-карамельный профиль, который безупречно рифмуется с карамелизованным луком, жареной корочкой и дымными нотами копченостей.")
        lines.append("• **Подача:** 14–16 °C в тюльпановидном бокале.")

    elif is_fortified and ("портвейн" in name.lower() or "portveyn" in wine_slug.lower()):
        lines.append("• **Европейская десертная:** премиальный горький шоколад (75–85%), шоколадный фондан с вишней, ореховые тарты.")
        lines.append("• **Сырная классика:** пикантные сыры с благородной голубой плесенью (Горгонзола Пиканте, Рокфор, Стилтон).")
        lines.append("• **Мясная гастрономия:** утиный паштет с брусничным джемом, сочный стейк с соусом из голубого сыра.")
        lines.append("\n**Почему подходит:**")
        lines.append(f"• **Химия вкуса:** бархатные танины ({tannins:.1f}/5) и природная сладость портвейна создают идеальную химическую синергию с солеными голубыми сырами: соль гасит избыток сладости, а ликерные тона сглаживают плесневую горечь.")
        lines.append("• **Выдержка:** многолетняя выдержка в дубовых бутах насыщает вино тонами чернослива в шоколаде, сафьяна и вяленого инжира, дополняющими десерты и паштеты.")
        lines.append("• **Подача:** 16–18 °C в дижестивном бокале.")

    elif is_sparkling:
        lines.append("• **Средиземноморская и морская:** свежие устрицы с лимоном, севиче из дикого лосося или тунца, жареные тигровые креветки.")
        lines.append("• **Праздничная русская:** красная икра на хрустящих тостах с вологодским сливочным маслом.")
        lines.append("• **Европейская легкая:** запеченный сыр Камамбер с розмарином и ягодами, прошутто с инжиром.")
        lines.append("\n**Почему подходит:**")
        lines.append(f"• **Химия вкуса:** живая бодрящая кислотность ({acidity:.1f}/5) в паре с мелким перляжем (пузырьками) моментально смывает жирную маслянистую пленку икры и рыбы, оставляя ощущение чистоты и легкости на нёбе.")
        lines.append("• **Выдержка:** классическая выдержка на дрожжевом осадке дает нежные тона французской бриоши и хрустящей корочки круассана.")
        lines.append("• **Подача:** 8–10 °C в бокале-тюльпане.")

    elif is_bold_red:
        lines.append("• **Кавказская и гриль:** мраморный стейк Рибай или Стриплойн средней прожарки (Medium) на углях с чесночным маслом.")
        lines.append("• **Русская и европейская:** томленая говяжья голяшка в соусе демигляс, жаркое из дичи или оленины с можжевельником.")
        lines.append("• **Сырная тарелка:** выдержанный Чеддер, Гауда от 12 месяцев, твердые фермерские сыры.")
        lines.append("\n**Почему подходит:**")
        lines.append(f"• **Химия вкуса:** выраженные танины ({max(tannins, 3.8):.1f}/5) — природные полифенолы — связываются с белком сочного мяса, устраняя вяжущее ощущение и раскрывая глубокие ягодные грани вина. Жирность стейка смягчает танинный каркас, а кислотность ({acidity:.1f}/5) освежает рецепторы.")
        lines.append("• **Выдержка:** контакт с дубом обогащает букет нотами черного перца, кедра и табака, усиливая аромат запеченной на огне мясной корочки.")
        lines.append("• **Подача:** 16–18 °C в объёмном бокале формы «Бордо».")

    elif "красн" in color:
        lines.append("• **Французская и европейская:** запеченная утиная грудка с брусничным соусом, паста с лесными грибами и трюфельным маслом.")
        lines.append("• **Домашняя мясная:** томленый кролик в белом вине с травами, рулет из индейки с черносливом.")
        lines.append("• **Сырная:** мягкие сыры с белой плесенью (Бри, Камамбер).")
        lines.append("\n**Почему подходит:**")
        lines.append(f"• **Химия вкуса:** деликатные шелковистые танины ({tannins:.1f}/5) не глушат тонкий вкус птицы, а ягодная кислотность балансирует подкожный утиный жир.")
        lines.append("• **Органолептика:** ноты спелой вишни и лесного подлеска идеально подчеркивают землистый вкус грибов.")
        lines.append("• **Подача:** 14–16 °C в бокале формы «Бургундия».")

    elif "бел" in color or "white" in cat:
        if has_oak or body >= 3.6:
            lines.append("• **Французская и североморская:** морские гребешки на сливочном масле с чесноком, лосось или форель в сливочно-икорном соусе.")
            lines.append("• **Итальянская:** паста Карбонара, ризотто с белыми грибами и пармезаном.")
            lines.append("• **Птица:** фермерский цыпленок в сливочно-горчичном соусе.")
            lines.append("\n**Почему подходит:**")
            lines.append(f"• **Химия вкуса:** сливочное плотное тело ({body:.1f}/5) и малолактическая мягкость вина безупречно совпадают по текстуре с топленым сливочным маслом и сливками, а умеренная кислотность ({acidity:.1f}/5) сохраняет свежесть.")
            lines.append("• **Выдержка:** выдержка в дубовых бочках дает тона ванили, тостов и жареного фундука, которые создают синергию с золотистой корочкой морепродуктов.")
            lines.append("• **Подача:** 11–13 °C в широком бокале для Шардоне.")
        else:
            lines.append("• **Средиземноморская:** сибас или дорадо на гриле с морской солью и розмарином, свежие мидии в чесночном бульоне.")
            lines.append("• **Паназиатская:** севиче из белой рыбы, сашими с авокадо и цитрусовым соусом понзу.")
            lines.append("• **Легкая сырная:** молодой козий сыр Шевр, моцарелла со спелыми томатами и базиликом.")
            lines.append("\n**Почему подходит:**")
            lines.append(f"• **Химия вкуса:** звонкая минеральная кислотность ({acidity:.1f}/5) работает как капля свежего лимонного сока — подчеркивает природную сладость нежного белка рыбы и устраняет маслянистость.")
            lines.append("• **Органолептика:** чистые цитрусово-персиковые и травянистые ноты освежают вкусовые рецепторы.")
            lines.append("• **Подача:** 9–11 °C.")

    elif "розов" in color:
        lines.append("• **Провансальская и средиземноморская:** салат Нисуаз с тунцом и фасолью, паэлья с морепродуктами и цыпленком.")
        lines.append("• **Гриль:** тигровые креветки на шпажках с паприкой, куриный шашлык с зеленью.")
        lines.append("• **Закуски:** брускетты с прошутто, мягкие козьи сыры.")
        lines.append("\n**Почему подходит:**")
        lines.append(f"• **Химия вкуса:** розе сочетает освежающую кислотность ({acidity:.1f}/5) белого вина и легкие ягодные танины красного, выступая идеальным гастрономическим мостом между рыбой и мясом.")
        lines.append("• **Подача:** 10–12 °C.")

    else:
        lines.append("• **Европейская классика:** фермерское сырное плато с орехами и медом, мясные деликатесы.")
        lines.append("• **Горячие блюда:** запеченное мясо птицы с травами или рыба на углях.")
        lines.append("\n**Почему подходит:**")
        lines.append(f"• **Химия вкуса:** сбалансированная кислотность ({acidity:.1f}/5) и тело ({body:.1f}/5) создают гармонию с блюдами умеренной плотности.")
        lines.append("• **Подача:** 12–14 °C.")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# 4. Вкусовой профиль вина (Опиши вкус, кислотность и танины)
# -----------------------------------------------------------------------------

def render_taste_profile_answer(wine: dict, wine_slug: str = "") -> str:
    """Формирует структурированное дегустационное описание вкуса, кислотности и танинов."""
    hist = HISTORICAL_WINES_DB.get(wine_slug) if wine_slug else None
    if hist and len(hist.wine_name) > len(wine.get("name", "")):
        name = hist.wine_name
    else:
        name = wine.get("name", "выбранное вино")
    color = (wine.get("color") or wine.get("category") or "").lower()
    features = wine.get("features") or {}
    desc = wine.get("description") or ""

    acidity = float(features.get("acidity") or 3.8)
    tannins = float(features.get("tannin") or 2.5)
    body = float(features.get("body") or 3.8)
    sweetness_code = features.get("sweetness") or 0
    sweetness_map = {0: "Сухое (до 4 г/л сахара)", 1: "Полусухое (4–18 г/л)", 2: "Полусладкое (18–45 г/л)", 3: "Сладкое / Десертное (от 45 г/л)"}
    sweetness_desc = sweetness_map.get(sweetness_code, "Сухое")

    # Словесные градации
    acid_word = "Умеренная, мягкая" if acidity < 3.2 else ("Сбалансированная, живая" if acidity <= 4.0 else "Яркая, бодрящая")
    tannin_word = "Шелковистые, деликатные" if tannins < 2.5 else ("Ощутимые, бархатистые" if tannins <= 3.8 else "Мощные, структурные")
    body_word = "Легкое, освежающее" if body < 3.0 else ("Среднетелое, гармоничное" if body <= 4.0 else "Полнотелое, глубокое")

    aromas = features.get("aroma") or []
    aroma_str = ", ".join(aromas) if aromas else "ягоды, полевые травы, фруктовые оттенки"

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
        # Берем ключевую выжимку из описания
        clean_desc = desc[:300].strip().rstrip(".") + "."
        lines.append(f"\n**Дегустационная заметка:**\n«{clean_desc}»")

    serve_temp = "16–18" if "красн" in color else ("8–10" if "игрист" in name.lower() else "10–12")
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


def render_analogs_answer(wine: dict, alternatives: list) -> Tuple[str, list]:
    """Формирует понятный текст и карточки вин-аналогов из российского каталога."""
    name = wine.get("name", "выбранное вино")
    if not alternatives:
        text = f"К вину «{name}» в текущем срезе каталога прямых близнецов не найдено. Рекомендуем обратить внимание на автохтонные российские позиции того же цвета и сладости."
        return text, []

    lines = [
        f"### Российские аналоги к вину «{name}»\n",
        f"Подобрал {len(alternatives)} близких по стилю и вкусовому балансу российских вин из каталога:\n"
    ]
    picks = []
    for i, a in enumerate(alternatives, 1):
        p_name = a.get("name") or "Российское вино"
        winery = a.get("winery") or ""
        facts = a.get("facts") or ""
        score = a.get("score") or 0.85
        score_pct = int(score * 100) if score <= 1.0 else int(score)
        reasons = a.get("reasons") or []
        reason_txt = "; ".join(reasons[:2]) if reasons else "Схожий сортовой состав и баланс кислотности"

        lines.append(f"**{i}. {p_name}** ({winery}) — сходство {score_pct}%")
        lines.append(f"   • {reason_txt}.")

        picks.append({
            "id": a.get("id"),
            "name": p_name,
            "winery": winery,
            "score": score_pct,
            "role": "Близкий аналог",
            "facts": facts,
            "quote": reason_txt,
            "image_url": a.get("image_url") or f"/api/image/{a.get('id')}"
        })

    return "\n".join(lines), picks
