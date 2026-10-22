from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool

try:
    from sommelier.schemas import (
        SommelierAlternative,
        SommelierAlternativesResponse,
        SommelierAskRequest,
        SommelierAskResponse,
        SommelierResetRequest,
        SommelierWineInfoResponse,
    )
    from sommelier.service import SommelierService
except ImportError:
    from app.schemas.sommelier import (
        SommelierAlternative,
        SommelierAlternativesResponse,
        SommelierAskRequest,
        SommelierAskResponse,
        SommelierResetRequest,
        SommelierWineInfoResponse,
    )
    from app.services.sommelier_service import SommelierService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sommelier", tags=["sommelier"])


def _service(request: Request) -> SommelierService:
    service: SommelierService | None = getattr(request.app.state, "sommelier", None)
    if service is None or not service.available:
        raise HTTPException(status_code=503, detail="sommelier catalog is not loaded")
    return service


def _resolve_image_url(request: Request, slug: str) -> str | None:
    """Определяет URL фото бутылки: из каталога WineCatalog VINA или стандартного эндпоинта."""
    catalog = getattr(request.app.state, "catalog", None)
    if catalog and hasattr(catalog, "wines_by_slug") and slug in catalog.wines_by_slug:
        return f"/api/image/{slug}"
    return None


@router.post("/ask", response_model=SommelierAskResponse)
async def ask(payload: SommelierAskRequest, request: Request) -> SommelierAskResponse:
    """Диалоговая точка входа: свободный текст -> рекомендация/справка/уточнение/отказ (guardrails).

    Первый вызов без `session_id` открывает новую сессию (её id возвращается в ответе и должен передаваться
    в последующих сообщениях того же диалога — контекст блюда/предпочтений/обратной связи хранится по сессии).
    """
    service = _service(request)
    session_id, sommelier = service.session(payload.session_id)
    
    query = (payload.message or payload.text or "").strip()
    if not query:
        raise HTTPException(status_code=422, detail="Поле 'message' или 'text' обязательно")

    result = await run_in_threadpool(sommelier.ask, query, payload.wine_slug)
    picks = result.get("picks", [])

    # Разрешение изображений бутылок из каталога VINA
    resolved_picks = []
    for pick in picks:
        p_id = pick.get("id")
        img_url = pick.get("image_url") or _resolve_image_url(request, p_id)
        resolved_picks.append({**pick, "image_url": img_url})

    return SommelierAskResponse(
        session_id=session_id,
        kind=result["kind"],
        text=result["text"],
        picks=resolved_picks,
        types=result.get("types", []),
        pool=result.get("pool"),
        total=result.get("total"),
        context=result.get("context"),
        dish_traits=result.get("dish_traits", []),
        note=result.get("note"),
    )


@router.post("/reset")
async def reset(payload: SommelierResetRequest, request: Request) -> dict[str, bool]:
    """Начинает диалог заново (тот же session_id, пустой контекст)."""
    service = _service(request)
    if not payload.session_id:
        return {"ok": True}
    ok = await run_in_threadpool(service.reset, payload.session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="unknown session_id")
    return {"ok": True}


@router.get("/wine/{slug}", response_model=SommelierWineInfoResponse)
async def wine_info(slug: str, request: Request, dish: str | None = Query(None, max_length=500)) -> SommelierWineInfoResponse:
    """Точка интеграции с распознаванием этикеток: slug товара из `/api/v1/search` -> справка сомелье по нему,
    и, если передан `dish` (текст блюда), оценка сочетания по правилам движка."""
    service = _service(request)
    sommelier = await run_in_threadpool(service.wine_lookup)
    dish_parsed = None
    if dish:
        try:
            from sommelier.dishes import parse_dish
        except ImportError:
            from app.sommelier.dishes import parse_dish

        dish_parsed = await run_in_threadpool(parse_dish, dish)
    result = await run_in_threadpool(sommelier.about_wine, slug, dish_parsed, dish)
    return SommelierWineInfoResponse(
        kind=result["kind"],
        id=result.get("id"),
        text=result["text"],
        card=result.get("card"),
        profile=result.get("profile"),
        pairing=result.get("pairing"),
        best_dishes=result.get("best_dishes", []),
        note=result.get("note"),
    )


@router.get("/wine/{slug}/alternatives", response_model=SommelierAlternativesResponse)
async def wine_alternatives(
    slug: str,
    request: Request,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> SommelierAlternativesResponse:
    """Точка интеграции с распознаванием: похожие по стилю вина каталога к распознанному вину (slug).

    Цвет и игристость совпадают, сладость отличается не больше чем на ступень; дальше — сорт, тип, тело, танины,
    ароматика и регион из карточек. Не больше двух вин одной винодельни.
    """
    service = _service(request)
    sommelier = await run_in_threadpool(service.wine_lookup)
    result = await run_in_threadpool(sommelier.alternatives, slug, limit)
    items = []
    for item in result.get("items", []):
        img_url = item.get("image_url") or _resolve_image_url(request, item.get("id"))
        items.append(SommelierAlternative(**{**item, "image_url": img_url}))

    return SommelierAlternativesResponse(kind=result["kind"], id=result.get("id"), items=items)
