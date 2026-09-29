from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_chat, routes_files, routes_system, routes_voice
from app.config import get_settings
from app.context import AppContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    ctx = await AppContext.create()
    app.state.ctx = ctx
    if settings.has_api_key:
        logger.info("NVIDIA NIM en %s", settings.nvidia_base_url)
    else:
        logger.warning(
            "NVIDIA_API_KEY no esta configurada. Copia .env.example a .env antes de usar el chat."
        )
    logger.info("Datos en %s", settings.data_root)
    try:
        yield
    finally:
        await ctx.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Chatbot multimodal Nemotron",
        description=(
            "Chat con Nemotron 3 (texto, razonamiento), Nemotron 3 Nano Omni "
            "(imagen, video y voz), Parakeet (ASR), Chatterbox (TTS) y nemotron-3-embed (RAG)."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(routes_system.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_files.router)
    app.include_router(routes_voice.router)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"service": "chatbot-multimodal-nemotron", "docs": "/docs"}

    return app


app = create_app()
