from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.context import get_context
from app.schemas import HealthResponse, ModelListResponse, ProbeResult
from app.services import media

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["system"])

PROBE_TARGETS: list[tuple[str, str]] = [
    ("text", "model_text_default"),
    ("omni", "model_omni"),
    ("embed", "model_embed"),
    ("ocr", "model_ocr"),
    ("asr", "model_asr"),
    ("tts", "model_tts"),
    ("safety", "model_safety"),
]


@router.get("/models", response_model=ModelListResponse)
async def list_models(request: Request) -> ModelListResponse:
    ctx = get_context(request)
    return ModelListResponse(models=ctx.router.for_ui(), default=ctx.settings.model_text_default)


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    ctx = get_context(request)
    settings = ctx.settings

    limits: dict[str, int | float] = {
        "max_image_mb": settings.max_image_mb,
        "max_video_mb": settings.max_video_mb,
        "max_video_seconds": settings.max_video_seconds,
        "max_audio_mb": settings.max_audio_mb,
        "max_audio_seconds": settings.max_audio_seconds,
        "max_doc_mb": settings.max_doc_mb,
        "max_doc_pages": settings.max_doc_pages,
        "file_ttl_hours": settings.file_ttl_hours,
    }

    if not settings.has_api_key:
        return HealthResponse(
            status="sin_api_key",
            api_key_configured=False,
            base_url=settings.nvidia_base_url,
            ffmpeg_available=media.ffmpeg_available(),
            rag_available=ctx.rag.available,
            limits=limits,
        )

    async def probe(role: str, attr: str) -> ProbeResult:
        model = getattr(settings, attr)
        if role in {"embed", "ocr", "asr", "tts"}:
            return ProbeResult(model=model, role=role, ok=True, detail="endpoint no verificado")
        ok, detail = await ctx.client.probe(model)
        return ProbeResult(model=model, role=role, ok=ok, detail=detail)

    results = await asyncio.gather(*(probe(role, attr) for role, attr in PROBE_TARGETS))
    healthy = all(item.ok for item in results if item.role in {"text", "omni"})

    return HealthResponse(
        status="ok" if healthy else "degradado",
        api_key_configured=True,
        base_url=settings.nvidia_base_url,
        ffmpeg_available=media.ffmpeg_available(),
        rag_available=ctx.rag.available,
        models=list(results),
        limits=limits,
    )


@router.get("/knowledge/search")
async def search_knowledge(
    request: Request,
    q: str = Query(min_length=2),
    top_k: int = Query(default=5, ge=1, le=20),
) -> dict:
    ctx = get_context(request)
    if not ctx.rag.available:
        raise HTTPException(
            status_code=503,
            detail="El RAG no esta disponible. Revisa que chromadb este instalado y ENABLE_RAG=true.",
        )
    hits = await ctx.rag.search(q, top_k)
    return {"query": q, "hits": [hit.model_dump() for hit in hits]}
