from __future__ import annotations

import base64
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.context import get_context
from app.schemas import FileKind, SpeakResponse, TranscribeResponse
from app.services import media
from app.services.nvidia_client import NvidiaError
from app.services.vision import transcribe_audio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voice", tags=["voice"])

CHUNK = 1024 * 1024


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    voice: str | None = None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(request: Request, file: UploadFile = File(...)) -> TranscribeResponse:  # noqa: B008
    ctx = get_context(request)
    settings = ctx.settings
    if not settings.has_api_key:
        raise HTTPException(status_code=503, detail="Falta NVIDIA_API_KEY en backend/.env.")

    if not file.filename:
        raise HTTPException(status_code=400, detail="El audio no tiene nombre.")

    suffix = Path(file.filename).suffix.lower() or ".webm"
    temp = settings.uploads_dir / f"voice_{uuid.uuid4().hex}{suffix}"
    size = 0
    try:
        with temp.open("wb") as handle:
            while chunk := await file.read(CHUNK):
                size += len(chunk)
                handle.write(chunk)
    finally:
        await file.close()

    try:
        if size > settings.max_audio_mb * media.MB:
            raise HTTPException(
                status_code=413,
                detail=f"El audio supera el limite de {settings.max_audio_mb} MB.",
            )
        await media.validate_media_limits(FileKind.audio, temp, settings)
        text, used_fallback = await transcribe_audio(ctx.client, ctx.router, settings, temp)
    except media.MediaError as exc:
        temp.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NvidiaError as exc:
        temp.unlink(missing_ok=True)
        raise HTTPException(status_code=502, detail=f"NVIDIA rechazo la peticion: {exc}") from exc
    finally:
        temp.unlink(missing_ok=True)

    return TranscribeResponse(
        text=text,
        model=ctx.router.asr(),
        language=settings.ui_language,
        used_fallback=used_fallback,
    )


@router.post("/speak", response_model=SpeakResponse)
async def speak(request: Request, body: SpeakRequest) -> SpeakResponse:
    ctx = get_context(request)
    if not ctx.settings.enable_tts:
        raise HTTPException(status_code=501, detail="El TTS esta deshabilitado (ENABLE_TTS=false).")
    if not ctx.settings.has_api_key:
        raise HTTPException(status_code=503, detail="Falta NVIDIA_API_KEY en backend/.env.")

    try:
        audio = await ctx.client.speak(
            ctx.router.tts(), body.text, voice=body.voice, language=ctx.settings.ui_language
        )
    except NvidiaError as exc:
        raise HTTPException(status_code=502, detail=f"NVIDIA rechazo la peticion: {exc}") from exc

    if not audio:
        raise HTTPException(status_code=502, detail="El servicio de voz devolvio una respuesta vacia.")

    return SpeakResponse(
        audio_base64=base64.b64encode(audio).decode("ascii"),
        mime="audio/wav",
        model=ctx.router.tts(),
        voice=body.voice,
    )


__all__ = ["router"]
