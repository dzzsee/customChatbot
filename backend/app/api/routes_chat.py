from __future__ import annotations

import base64
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.context import get_context
from app.prompts import RAG_CONTEXT_HEADER, chat_system_prompt
from app.schemas import ChatRequest, FileKind
from app.services.nvidia_client import NvidiaError, image_part, text_part, video_part

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_context_blocks(
    attachments: list[dict], rag_blocks: list[str], inline_media: bool | None
) -> tuple[list[dict], list[str]]:
    """Devuelve (partes multimodales, bloques de texto de analisis).

    Reenviar imagenes es barato y mejora las respuestas, asi que es el valor por
    defecto. Los videos pesan mucho: solo se reenvian si se piden explicitamente.
    """
    from pathlib import Path  # noqa: PLC0415

    inline: list[dict] = []
    text_blocks: list[str] = []
    for attachment in attachments:
        name = attachment["name"]
        kind = FileKind(attachment["kind"])
        stored_path = attachment.get("stored_path")
        analysis = attachment.get("analysis") or ""
        text_blocks.append(f"### {name} ({kind.value})\n{analysis}")

        if inline_media is False or not stored_path:
            continue

        path = Path(stored_path)
        if not path.exists():
            continue
        if kind is FileKind.image:
            inline.append(image_part(path.read_bytes(), attachment["mime"]))
        elif kind is FileKind.video and inline_media is True:
            inline.append(video_part(path.read_bytes(), "video/mp4"))
    return inline, text_blocks


async def stream_chat(request: Request, body: ChatRequest) -> AsyncIterator[str]:
    ctx = get_context(request)
    settings = ctx.settings

    last_user = next(
        (m for m in reversed(body.messages) if m.role.value == "user" and m.content.strip()),
        None,
    )
    if last_user is None:
        yield sse("error", {"message": "El mensaje no puede estar vacio."})
        return

    allowed, reason = await ctx.guard.check(last_user.content, role="user")
    if not allowed:
        yield sse("blocked", {"message": reason or "El mensaje fue bloqueado por la moderacion."})
        return

    wanted_ids = list(dict.fromkeys(body.attachment_ids + last_user.attachment_ids))
    attachments: list[dict] = []
    for file_id in wanted_ids:
        row = await ctx.db.get_row(file_id)
        if row is None:
            yield sse("error", {"message": f"El archivo {file_id} no existe o ya fue eliminado."})
            return
        attachments.append(row)

    rag_blocks: list[str] = []
    if body.use_rag and ctx.rag.available and last_user.content.strip():
        hits = await ctx.rag.search(last_user.content)
        rag_blocks = [f"[{hit.name or 'archivo'}]: {hit.text}" for hit in hits]

    inline_parts, analysis_blocks = build_context_blocks(attachments, rag_blocks, body.inline_media)
    context_blocks = analysis_blocks + rag_blocks

    spec = ctx.router.text(body.model, reasoning=body.reasoning)
    if attachments and not any(part.get("type") in {"image_url", "video_url"} for part in inline_parts):
        spec.model = ctx.settings.model_omni

    candidates = [spec]
    if spec.model == settings.model_text_default and settings.model_text_lightning != spec.model:
        candidates.append(ctx.router.text(settings.model_text_lightning, reasoning=False))

    yield sse("meta", {"model": spec.model, "attachments": len(attachments), "rag_hits": len(rag_blocks)})

    system_prompt = chat_system_prompt(settings.ui_language, context_blocks)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    for message in body.messages:
        if message.role.value == "system":
            continue
        messages.append({"role": message.role.value, "content": message.content})

    if not messages[-1]["content"] and inline_parts:
        messages[-1]["content"] = "Analiza el archivo adjunto."
    if inline_parts:
        messages[-1]["content"] = [
            text_part(messages[-1]["content"] or "Analiza el archivo adjunto."),
            *inline_parts,
        ]

    reasoning_text: list[str] = []
    content_text: list[str] = []
    for index, candidate in enumerate(candidates):
        try:
            async for event in ctx.client.chat_stream(
                candidate.model,
                messages,
                max_tokens=candidate.max_tokens,
                temperature=candidate.temperature,
                top_p=candidate.top_p,
                top_k=candidate.top_k,
                thinking=candidate.thinking,
            ):
                if event["type"] == "reasoning":
                    reasoning_text.append(event["delta"])
                    yield sse("reasoning", {"delta": event["delta"]})
                elif event["type"] == "delta":
                    content_text.append(event["delta"])
                    yield sse("delta", {"delta": event["delta"]})
            if index > 0:
                yield sse("meta", {"model": candidate.model})
            break
        except NvidiaError as exc:
            can_fallback = (
                index + 1 < len(candidates)
                and not content_text
                and not reasoning_text
                and "404" in str(exc)
            )
            if can_fallback:
                logger.warning("Modelo %s no disponible; usando %s", candidate.model, candidates[index + 1].model)
                continue
            logger.warning("Fallo de streaming: %s", exc)
            yield sse("error", {"message": f"NVIDIA rechazo la peticion: {exc}"})
            return

    answer = "".join(content_text)

    if settings.enable_tts and body.speak and answer.strip():
        try:
            audio = await ctx.client.speak(ctx.router.tts(), answer)
            yield sse(
                "audio",
                {
                    "audio_base64": base64.b64encode(audio).decode("ascii"),
                    "mime": "audio/wav",
                },
            )
        except NvidiaError as exc:
            logger.warning("TTS fallo: %s", exc)
            yield sse("warning", {"message": f"No se pudo generar el audio: {exc}"})

    yield sse("done", {"content": answer, "reasoning": "".join(reasoning_text)})


@router.post("/stream")
async def chat_stream(request: Request, body: ChatRequest) -> StreamingResponse:
    if not get_context(request).settings.has_api_key:
        raise HTTPException(
            status_code=503,
            detail="Falta NVIDIA_API_KEY. Copia backend/.env.example a backend/.env y anade tu clave.",
        )
    return StreamingResponse(
        stream_chat(request, body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
