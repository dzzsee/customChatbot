from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings
from app.prompts import (
    AUDIO_TRANSCRIBE_PROMPT,
    IMAGE_ANALYSIS_PROMPT,
    PDF_ANALYSIS_PROMPT,
    VIDEO_ANALYSIS_PROMPT,
)
from app.services import media
from app.services.nvidia_client import (
    audio_part,
    image_part,
    text_part,
    video_part,
)
from app.services.router import ModelRouter

logger = logging.getLogger(__name__)


def language_suffix(ui_language: str) -> str:
    if ui_language.lower().startswith("es"):
        return "\n\nEscribe tu respuesta completa en español."
    return "\n\nWrite your entire answer in English."


async def analyze_image(
    client,
    router: ModelRouter,
    settings: Settings,
    data: bytes,
    mime: str,
    *,
    prompt: str | None = None,
) -> str:
    base_prompt = prompt or IMAGE_ANALYSIS_PROMPT
    spec = router.image(reasoning=prompt is not None)
    messages = [
        {
            "role": "user",
            "content": [
                text_part(base_prompt + language_suffix(settings.ui_language)),
                image_part(data, mime),
            ],
        }
    ]
    _, content = await client.complete(
        spec.model,
        messages,
        max_tokens=spec.max_tokens,
        temperature=spec.temperature,
        top_p=spec.top_p,
        top_k=spec.top_k,
        thinking=spec.thinking,
    )
    return content.strip()


async def analyze_video(
    client,
    router: ModelRouter,
    settings: Settings,
    source: Path,
    workdir: Path,
    *,
    prompt: str | None = None,
) -> tuple[str, Path]:
    """Normaliza a MP4, lo envia a Omni y devuelve (analisis, ruta_del_mp4)."""
    mp4_path = await media.normalize_video_to_mp4(source, workdir / f"{source.stem}.mp4")
    payload = mp4_path.read_bytes()

    logger.info("Enviando video a Omni: %.1f MB (%.1f MB en base64)", len(payload) / 1e6, len(payload) * 1.33 / 1e6)

    spec = router.video()
    base_prompt = prompt or VIDEO_ANALYSIS_PROMPT
    messages = [
        {
            "role": "user",
            "content": [
                text_part(base_prompt + language_suffix(settings.ui_language)),
                video_part(payload, "video/mp4"),
            ],
        }
    ]
    _, content = await client.complete(
        spec.model,
        messages,
        max_tokens=spec.max_tokens,
        temperature=spec.temperature,
        top_p=spec.top_p,
        top_k=spec.top_k,
        thinking=spec.thinking,
        extra_body=spec.extra_body,
    )
    return content.strip(), mp4_path


async def transcribe_audio(
    client,
    router: ModelRouter,
    settings: Settings,
    source: Path,
) -> tuple[str, bool]:
    """Transcribe con Parakeet ES. Si el endpoint no responde, cae a Nemotron Omni.

    Devuelve (texto, uso_fallback).
    """
    from app.services.nvidia_client import guess_mime  # noqa: PLC0415

    original = source.read_bytes()
    filename = source.name

    if media.ffmpeg_available():
        wav_path = source.with_suffix(".16k.wav")
        extracted = await media.extract_audio(source, wav_path)
        if extracted is not None:
            audio_bytes = extracted.read_bytes()
            filename = extracted.name
        else:
            audio_bytes = original
    else:
        audio_bytes = original

    try:
        text, _ = await client.transcribe(router.asr(), audio_bytes, filename)
        if text:
            return text, False
        logger.warning("Parakeet devolvio una transcripcion vacia, probando con Omni.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Parakeet fallo (%s), usando Nemotron Omni como alternativa.", exc)

    spec = router.image(reasoning=False)
    spec.max_tokens = 4096
    messages = [
        {
            "role": "user",
            "content": [
                text_part(AUDIO_TRANSCRIBE_PROMPT + language_suffix(settings.ui_language)),
                audio_part(audio_bytes, guess_mime(filename, "audio/wav")),
            ],
        }
    ]
    _, content = await client.complete(
        spec.model,
        messages,
        max_tokens=spec.max_tokens,
        temperature=spec.temperature,
        top_p=spec.top_p,
        top_k=spec.top_k,
        thinking=False,
    )
    return content.strip(), True


async def analyze_document(
    client,
    router: ModelRouter,
    settings: Settings,
    source: Path,
    *,
    max_pages: int | None = None,
) -> tuple[str, int | None, list[bytes]]:
    """Analiza un documento. Devuelve (analisis, paginas, imagenes_de_paginas).

    Para PDF: extrae texto si existe; si el PDF es escaneado, rasteriza las paginas
    y las envia a Omni como imagenes.
    """
    limit = max_pages or settings.max_doc_pages
    suffix = source.suffix.lower()

    if suffix == ".pdf":
        text, page_count, page_images = media.extract_pdf(source, limit)
        has_text_layer = len(text) > 200 and "sin capa de texto" not in text

        if has_text_layer:
            spec = router.image(reasoning=True)
            spec.max_tokens = 8192
            messages = [
                {
                    "role": "user",
                    "content": [
                        text_part(PDF_ANALYSIS_PROMPT + language_suffix(settings.ui_language)),
                        text_part(f"\n\nNombre del archivo: {source.name}\n\n{text}"),
                    ],
                }
            ]
            _, content = await client.complete(
                spec.model,
                messages,
                max_tokens=spec.max_tokens,
                temperature=spec.temperature,
                top_p=spec.top_p,
                top_k=spec.top_k,
                thinking=True,
            )
            return content.strip(), page_count, page_images

        return _analyze_page_images(client, router, settings, page_images, source.name), page_count, page_images

    if suffix == ".docx":
        text = media.extract_docx(source)
    else:
        text = media.extract_plain_text(source)

    if not text.strip():
        raise media.MediaError(f"El documento {source.name} no contiene texto legible.")

    spec = router.image(reasoning=True)
    spec.max_tokens = 8192
    messages = [
        {
            "role": "user",
            "content": [
                text_part(PDF_ANALYSIS_PROMPT + language_suffix(settings.ui_language)),
                text_part(f"\n\nNombre del archivo: {source.name}\n\n{text}"),
            ],
        }
    ]
    _, content = await client.complete(
        spec.model,
        messages,
        max_tokens=spec.max_tokens,
        temperature=spec.temperature,
        top_p=spec.top_p,
        top_k=spec.top_k,
        thinking=True,
    )
    return content.strip(), None, []


async def _analyze_page_images(
    client, router: ModelRouter, settings: Settings, page_images: list[bytes], name: str
) -> str:
    """Envia paginas renderizadas a Omni. Una pagina por peticion, en paralelo."""
    import asyncio  # noqa: PLC0415

    spec = router.document_images()
    prompt = (
        "Describe this scanned document page: read all visible text verbatim, "
        "describe tables, figures and layout, and note anything incomplete or cut off."
        + language_suffix(settings.ui_language)
    )

    async def one(index: int, image: bytes) -> str:
        messages = [
            {
                "role": "user",
                "content": [text_part(prompt), image_part(image, "image/png")],
            }
        ]
        try:
            _, content = await client.complete(
                spec.model,
                messages,
                max_tokens=2048,
                temperature=spec.temperature,
                top_p=spec.top_p,
                top_k=spec.top_k,
                thinking=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudo analizar la pagina %d: %s", index + 1, exc)
            return f"--- Pagina {index + 1} ---\n[No se pudo analizar esta pagina: {exc}]"
        return f"--- Pagina {index + 1} ---\n{content.strip()}"

    results = await asyncio.gather(*(one(i, img) for i, img in enumerate(page_images)))
    header = f"Analisis del documento escaneado **{name}** ({len(page_images)} pagina(s)):\n\n"
    return header + "\n\n".join(results)
