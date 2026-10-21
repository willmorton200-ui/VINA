"""AI-сомелье по каталогу вин: детерминированный движок подбора + необязательный LLM-слой для речи.

Все факты о вине берутся из `data/wines_integrated.csv` (см. `catalog.py`); LLM (`llm.py`), если включён, только формулирует ответ
и проверяется на соответствие выдаче движка. Подробности слоёв — в `docs/SOMMELIER.md` и `README.md`.
"""
from .sommelier import Sommelier
from .service import SommelierService
from .dialog_router import router as dialog_router
from .pairing_router import router as pairing_router

__all__ = ["Sommelier", "SommelierService", "dialog_router", "pairing_router"]
