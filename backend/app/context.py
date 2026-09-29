from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import Settings, get_settings
from app.db import Database
from app.services.nvidia_client import NvidiaClient
from app.services.rag import RagStore
from app.services.router import ModelRouter
from app.services.safety import SafetyGuard

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContext:
    settings: Settings
    client: NvidiaClient
    router: ModelRouter
    db: Database
    rag: RagStore
    guard: SafetyGuard

    @classmethod
    async def create(cls) -> AppContext:
        settings = get_settings()
        client = NvidiaClient(settings)
        db = Database(settings)
        await db.start()
        rag = RagStore(settings, client)
        await rag.start()
        return cls(
            settings=settings,
            client=client,
            router=ModelRouter(settings),
            db=db,
            rag=rag,
            guard=SafetyGuard(settings, client),
        )

    async def close(self) -> None:
        await self.db.cleanup_expired()
        await self.db.stop()
        await self.client.aclose()


def get_context(request) -> AppContext:
    ctx: AppContext | None = getattr(request.app.state, "ctx", None)
    if ctx is None:  # pragma: no cover
        raise RuntimeError("El contexto de la aplicacion no esta inicializado.")
    return ctx
