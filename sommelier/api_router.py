import asyncio
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import numpy as np

# Универсальный импорт (работает и из sommelier/, и из sommelier/sommelier/)
try:
    from .pairing_engine import SommelierPairingEngine, DishBuilderInput
    from .stores_and_history import (
        HISTORICAL_WINES_DB,
        get_simple_and_unusual_dishes,
        get_5_nearest_walking_stores,
        generate_sommelier_toast_and_advice,
    )
except ImportError:
    from sommelier.pairing_engine import SommelierPairingEngine, DishBuilderInput
    from sommelier.stores_and_history import (
        HISTORICAL_WINES_DB,
        get_simple_and_unusual_dishes,
        get_5_nearest_walking_stores,
        generate_sommelier_toast_and_advice,
    )

sommelier_router = APIRouter(prefix="/api/v2", tags=["VINA Sommelier & Map"])

# Демо-каталог с историческими винами (автоматически объединяется с вашим основным каталогом VINA)
DEMO_CATALOG = [
    {
        "slug": "massandra-portveyn-krasnyy-livadiya",
        "name": "Портвейн Красный Ливадия Массандра",
        "winery": "Массандра",
        "alcohol": "18.5%",
        "description": "Легендарный марочный красный портвейн, созданный князем Львом Голицыным в 1891 году для императорского подвала в Ливадии. Подавался на Ялтинской конференции 1945 года лидерам антигитлеровской коалиции.",
        "color": "Красное",
        "sugar": "Сладкое (Ликерное)",
        "grape": "Каберне Совиньон",
        "region": "Крым, Южный берег",
        "price": 1490,
        "rating": 4.9,
        "has_history": True,
        "acidity": 3.8,
        "tannins": 3.9,
        "body": 4.9,
        "sweetness": 4.6,
        "oak_intensity": 4.8,
    },
    {
        "slug": "massandra-madera-krymskaya",
        "name": "Мадера Массандра Крымская Выдержанная",
        "winery": "Массандра",
        "alcohol": "19.5%",
        "description": "Классическая крымская выдержанная мадера («дважды рожденное солнцем вино»), созревавшая в дубовых бочках на солнечных площадках не менее 5 лет.",
        "color": "Белое",
        "sugar": "Сухое / Крепленое",
        "grape": "Серсиаль, Вердельо, Альбильо",
        "region": "Крым",
        "price": 1150,
        "rating": 4.8,
        "has_history": True,
        "acidity": 4.3,
        "tannins": 1.6,
        "body": 4.5,
        "sweetness": 2.2,
        "oak_intensity": 4.9,
    },
    {
        "slug": "golubitskoe-estate-rose-rozovoe-suhoe-125",
        "name": "Голубицкое Эстейт Розе",
        "winery": "Голубицкое Эстейт",
        "alcohol": "12.5%",
        "description": "Элегантное сухое розе из сорта Пино Нуар с освежающими тонами лесной земляники, малины и минеральным послевкусием.",
        "color": "Розовое",
        "sugar": "Сухое",
        "grape": "Пино Нуар",
        "region": "Кубань, Таманский п-ов",
        "price": 1090,
        "rating": 4.7,
        "has_history": False,
        "acidity": 4.2,
        "tannins": 1.8,
        "body": 3.2,
        "sweetness": 1.2,
        "oak_intensity": 1.5,
    },
    {
        "slug": "sikory-risling-semeynyy-rezerv-suhoe",
        "name": "Сикоры Рислинг Семейный Резерв",
        "winery": "Имение Сикоры",
        "alcohol": "13.0%",
        "description": "Премиальный рислинг терруара Семигорья с яркими нотами белых цветов, зеленого яблока, лайма и выразительной благородной кислотностью.",
        "color": "Белое",
        "sugar": "Сухое",
        "grape": "Рислинг",
        "region": "Кубань, Семигорье",
        "price": 1850,
        "rating": 4.8,
        "has_history": False,
        "acidity": 4.5,
        "tannins": 1.4,
        "body": 3.6,
        "sweetness": 1.1,
        "oak_intensity": 2.0,
    },
    {
        "slug": "fanagoria-saperavi-avtorskoe-krasnoe-suhoe",
        "name": "Фанагория Автохтон Саперави",
        "winery": "Фанагория",
        "alcohol": "13.5%",
        "description": "Насыщенное автохтонное сухое красное вино из сорта Саперави с глубоким гранатовым оттенком, нотами черных ягод, чернослива и шелковистыми танинами.",
        "color": "Красное",
        "sugar": "Сухое",
        "grape": "Саперави",
        "region": "Кубань, Тамань",
        "price": 790,
        "rating": 4.5,
        "has_history": False,
        "acidity": 3.7,
        "tannins": 4.2,
        "body": 4.4,
        "sweetness": 1.3,
        "oak_intensity": 3.5,
    },
    {
        "slug": "vedernikov-krasnostop-zolotovskiy-suhoe",
        "name": "Винодельня Ведерниковъ Красностоп Золотовский",
        "winery": "Винодельня Ведерниковъ",
        "alcohol": "14.0%",
        "description": "Флагманский донской автохтон из вековых лоз Красностопа Золотовского, выдержанный в дубовых бочках, с глубокими тонами черной смородины, кожи и шоколада.",
        "color": "Красное",
        "sugar": "Сухое",
        "grape": "Красностоп Золотовский",
        "region": "Долина Дона",
        "price": 1650,
        "rating": 4.8,
        "has_history": False,
        "acidity": 3.9,
        "tannins": 4.6,
        "body": 4.8,
        "sweetness": 1.2,
        "oak_intensity": 4.5,
    },
]

engine = SommelierPairingEngine(catalog_items=DEMO_CATALOG)


def bind_existing_vina_catalog(raw_catalog: Any) -> None:
    """Подключает реальный каталог WineCatalog из app.py ко всем модулям сомелье."""
    normalized_list = []

    if isinstance(raw_catalog, dict):
        iterator = raw_catalog.items()
    elif isinstance(raw_catalog, list):
        iterator = [(item.get("slug") or item.get("id"), item) for item in raw_catalog if isinstance(item, dict)]
    else:
        iterator = []

    for slug, info in iterator:
        if not slug or not isinstance(info, dict):
            continue
        item_copy = dict(info)
        item_copy["slug"] = str(slug)
        item_copy["remote_image_url"] = info.get("remote_image_url") or info.get("image_url") or ""
        item_copy["image_url"] = f"/api/image/{slug}"
        normalized_list.append(item_copy)

    # Исторические демо-вина идут первыми, затем все 2108 вин из базы VINA
    demo_list = []
    for d in DEMO_CATALOG:
        d_copy = dict(d)
        if not d_copy.get("image_url"):
            d_copy["image_url"] = f"/api/image/{d_copy['slug']}"
        demo_list.append(d_copy)

    merged = demo_list + normalized_list
    engine.load_catalog(merged)
    print(f"[Sommelier v2] Каталог успешно подключен: {len(engine.catalog)} вин в базе.")


@sommelier_router.get("/catalog/facets")
async def get_catalog_facets():
    """Возвращает уникальные списки регионов, виноделен, сортов и категорий для фильтров."""
    regions = set()
    wineries = set()
    grapes = set()
    categories = set()
    for item in engine.catalog.values():
        reg = item.get("region")
        if reg and str(reg).strip():
            regions.add(str(reg).strip())
        win = item.get("winery")
        if win and str(win).strip():
            wineries.add(str(win).strip())
        cat = item.get("category")
        if cat and str(cat).strip():
            categories.add(str(cat).strip())
        grp = item.get("grape")
        if grp:
            for g in str(grp).replace(";", ",").split(","):
                g_c = g.strip()
                if g_c and len(g_c) > 2:
                    grapes.add(g_c)
    return {
        "regions": sorted(list(regions)),
        "wineries": sorted(list(wineries))[:80],
        "grapes": sorted(list(grapes))[:80],
        "categories": sorted(list(categories)),
    }


@sommelier_router.get("/catalog")
async def list_catalog(
    color: Optional[str] = Query(None, description="Красное | Белое | Розовое"),
    sugar: Optional[str] = Query(None, description="Сухое | Полусухое | Сладкое"),
    category: Optional[str] = Query(None, description="Тихие | Игристые | Ликерные"),
    region: Optional[str] = Query(None, description="Регион"),
    winery: Optional[str] = Query(None, description="Винодельня / производитель"),
    grape: Optional[str] = Query(None, description="Сорт винограда"),
    min_rating: Optional[float] = Query(None, description="Минимальный рейтинг"),
    only_with_history: bool = Query(False, description="Показать только вина с историей"),
    dish_query: Optional[str] = Query(None, description="Быстрый фильтр под блюдо: steak | fish | cheese | dessert | poultry"),
    q: Optional[str] = Query(None, description="Текстовый поиск по названию или сорту"),
    limit: int = Query(24, description="Количество на страницу"),
    offset: int = Query(0, description="Смещение"),
):
    """Возвращает каталог вин с органолептикой, простыми/необычными блюдами и бейджем Истории."""
    matched = []
    for slug, item in engine.catalog.items():
        if color:
            col_l = color.lower()
            if col_l in ["игристое", "игристые"]:
                is_sparkling = any(k in f"{item.get('name', '')} {item.get('category', '')} {item.get('sugar', '')}".lower() for k in ["игрист", "брют", "шампан", "кава", "просекко", "франчакорта"])
                if not is_sparkling:
                    continue
            elif col_l not in str(item.get("color", "")).lower() and col_l not in str(item.get("category", "")).lower():
                continue
        if sugar and sugar.lower() not in str(item.get("sugar", "")).lower():
            continue
        if category and category.lower() not in str(item.get("category", "")).lower():
            continue
        if region and region.lower() not in str(item.get("region", "")).lower():
            continue
        if winery and winery.lower() not in str(item.get("winery", "")).lower():
            continue
        if grape and grape.lower() not in str(item.get("grape", "")).lower():
            continue

        has_hist = slug in HISTORICAL_WINES_DB or bool(item.get("has_history"))
        if only_with_history and not has_hist:
            continue

        if q:
            q_clean = q.lower().strip()
            text_haystack = f"{item.get('name', '')} {item.get('grape', '')} {item.get('winery', '')} {item.get('region', '')}".lower()
            if q_clean not in text_haystack:
                continue

        vec = engine.wine_vectors.get(slug)
        if not vec:
            vec = engine.infer_wine_vector(item)

        # Вычисляем стабильный рейтинг
        raw_r = item.get("rating")
        if raw_r:
            wine_rating = float(raw_r)
        else:
            wine_rating = round(4.68 + (abs(hash(slug)) % 31) / 100.0, 2)

        if min_rating and wine_rating < min_rating:
            continue

        # Фильтрация под тип блюда
        if dish_query:
            dq = dish_query.lower()
            if dq in ["steak", "bbq", "мясо"] and vec.tannins < 3.0:
                continue
            elif dq in ["fish", "рыба"] and vec.tannins > 2.3:
                continue
            elif dq in ["dessert", "десерт"] and vec.sweetness < 2.8:
                continue
            elif dq in ["poultry", "птица"] and (vec.acidity < 3.2 or vec.tannins > 3.8):
                continue

        matched.append((slug, item, vec, has_hist, wine_rating))

    total_count = len(matched)
    page_slice = matched[offset : offset + limit]

    results = []
    for slug, item, vec, has_hist, wine_rating in page_slice:
        quick_dishes = get_simple_and_unusual_dishes(
            acidity=vec.acidity,
            tannins=vec.tannins,
            body=vec.body,
            sweetness=vec.sweetness,
            wine_slug=slug,
        )

        results.append({
            **item,
            "slug": slug,
            "rating": wine_rating,
            "price": item.get("price") or (750 + (abs(hash(slug)) % 145) * 10),
            "has_history": has_hist,
            "organoleptic": vec.model_dump(),
            "quick_dishes": {
                "simple": [d.model_dump() for d in quick_dishes["simple"]],
                "unusual": [d.model_dump() for d in quick_dishes["unusual"]],
            },
        })

    return {
        "count": total_count,
        "items": results,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_count,
    }


@sommelier_router.get("/wine/{wine_slug}/full-sommelier")
async def get_wine_full_sommelier(wine_slug: str):
    """Заменяет примитивный текстовый сомелье в Сканере и Каталоге на полный разбор."""
    if wine_slug not in engine.catalog:
        raise HTTPException(status_code=404, detail="Вино не найдено в каталоге")

    item = engine.catalog[wine_slug]
    vec = engine.wine_vectors[wine_slug]
    dishes = engine.recommend_dishes_for_wine(wine_slug, top_k=4)
    analogs = engine.find_wine_analogs(wine_slug)
    quick_dishes = get_simple_and_unusual_dishes(
        vec.acidity, vec.tannins, vec.body, vec.sweetness, wine_slug
    )
    history = HISTORICAL_WINES_DB.get(wine_slug)

    return {
        "wine": item,
        "organoleptic": vec,
        "simple_dishes": quick_dishes["simple"],
        "unusual_dishes": quick_dishes["unusual"],
        "evidence_pairings": dishes,
        "analogs": analogs,
        "history": history,
    }


def _build_wine_set(wine_slug: str, count: int):
    """Генерация сета из `count` (2..7) подобных вин по стилю и органолептике."""
    count = max(2, min(7, count))
    if wine_slug not in engine.catalog:
        if engine.catalog:
            wine_slug = next(iter(engine.catalog.keys()))
        else:
            raise HTTPException(status_code=404, detail="Каталог пуст")

    base = engine.catalog[wine_slug]
    target_vec = engine.wine_vectors[wine_slug].to_numpy()
    target_color = str(base.get("color", "")).lower()
    weights = np.array([1.3, 1.4, 1.1, 1.6, 0.8], dtype=np.float32)

    scored = []
    for slug, item in engine.catalog.items():
        if slug == wine_slug:
            continue
        c_color = str(item.get("color", "")).lower()
        if target_color and c_color and (target_color[:4] != c_color[:4]):
            continue
        cand_vec = engine.wine_vectors[slug].to_numpy()
        dist = float(np.sqrt(np.sum(weights * ((target_vec - cand_vec) ** 2))))
        scored.append((dist, item))

    scored.sort(key=lambda x: x[0])
    similar_items = [x[1] for x in scored[:count - 1]]
    result_items = [base] + similar_items

    formatted = []
    for it in result_items:
        s = it.get("slug") or it.get("id")
        rating_val = str(it.get("rating") or "4.8")
        meta_parts = [
            it.get("region") or "Россия",
            f"{it.get('color') or 'Вино'}, {str(it.get('sugar') or 'сухое').lower()}",
            "0.75 л"
        ]
        formatted.append({
            "slug": s,
            "title": it.get("name") or it.get("title") or s,
            "winery": it.get("winery") or "Винодельня России",
            "meta": ", ".join(meta_parts),
            "rating": rating_val,
            "reviews": str(it.get("reviews") or "18"),
            "image_url": f"/api/image/{s}"
        })

    return {
        "base_wine": base,
        "count": len(formatted),
        "items": formatted
    }


@sommelier_router.get("/wine-set")
async def get_wine_set_endpoint(
    wine_slug: str = Query("loco-cimbali-blanc-de-neige-shardone-beloe-suhoe-131", description="Slug базового вина"),
    count: int = Query(4, ge=2, le=7, description="Количество вин в сете (от 2 до 7)")
):
    return _build_wine_set(wine_slug, count)


@sommelier_router.get("/wine/{wine_slug}/set")
async def get_wine_set_by_slug(
    wine_slug: str,
    count: int = Query(4, ge=2, le=7, description="Количество вин в сете (от 2 до 7)")
):
    return _build_wine_set(wine_slug, count)


@sommelier_router.get("/wine/{wine_slug}/history")
async def get_wine_history_story(wine_slug: str):
    """Возвращает историческое досье вина (знаменитости, Ялта 1945, история создания)."""
    if wine_slug not in HISTORICAL_WINES_DB:
        raise HTTPException(status_code=404, detail="Для этого вина историческое досье еще не заполнено")
    return HISTORICAL_WINES_DB[wine_slug]


@sommelier_router.get("/map/nearby-stores")
async def get_nearby_stores_endpoint(
    lat: float = Query(45.0355, description="Широта пользователя"),
    lon: float = Query(38.9753, description="Долгота пользователя"),
    wine_slug: Optional[str] = Query(None, description="Опциональный slug выбранного вина"),
):
    """Возвращает 5 ближайших магазинов в пешей доступности для карты OpenStreetMap."""
    price = 990
    wine_name = None
    if wine_slug and wine_slug in engine.catalog:
        w = engine.catalog[wine_slug]
        price = int(w.get("price") or 990)
        wine_name = w.get("name")

    stores = await asyncio.to_thread(get_5_nearest_walking_stores, user_lat=lat, user_lon=lon, wine_slug=wine_slug, base_price=price)
    return {
        "user_location": {"lat": lat, "lon": lon},
        "selected_wine_slug": wine_slug,
        "selected_wine_name": wine_name,
        "stores": stores,
    }


class SommelierAskRequest(BaseModel):
    occasion: str = "friends"
    question: str = ""
    wine_slug: Optional[str] = "massandra-portveyn-krasnyy-livadiya"


@sommelier_router.post("/sommelier/ask")
async def ask_sommelier_endpoint(req: SommelierAskRequest):
    """Закладка 'Сомелье': генерация тоста к событию и совета с привязкой к каталогу."""
    slug = req.wine_slug if req.wine_slug in engine.catalog else "massandra-portveyn-krasnyy-livadiya"
    wine = engine.catalog[slug]
    vec = engine.wine_vectors[slug]

    toast_data = generate_sommelier_toast_and_advice(
        occasion=req.occasion,
        user_question=req.question,
        wine_name=wine.get("name", slug),
        wine_slug=slug,
        acidity=vec.acidity,
        tannins=vec.tannins,
    )
    analogs = engine.find_wine_analogs(slug)
    return {
        "wine": wine,
        "organoleptic": vec,
        "toast": toast_data,
        "recommended_catalog_wines": analogs,
    }


@sommelier_router.post("/sommelier/dish-to-wine")
async def dish_to_wine_endpoint(builder: DishBuilderInput):
    """Подбор вина к выбранному блюду в Каталоге."""
    dish = engine.build_custom_dish_profile(builder)
    wines = engine.recommend_wines_for_dish(dish)
    return {"dish": dish, "wines": wines}