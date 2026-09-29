from __future__ import annotations

import asyncio
import base64
import logging
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any

import httpx
from openai import AsyncOpenAI

from app.config import Settings

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
MAX_RETRIES = 3
BACKOFF_SECONDS = 1.5

MIME_BY_SUFFIX: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}


def guess_mime(name: str, fallback: str = "application/octet-stream") -> str:
    return MIME_BY_SUFFIX.get(Path(name).suffix.lower(), fallback)


def to_data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def text_part(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def image_part(data: bytes, mime: str) -> dict[str, Any]:
    return {"type": "image_url", "image_url": {"url": to_data_url(data, mime)}}


def video_part(data: bytes, mime: str = "video/mp4") -> dict[str, Any]:
    return {"type": "video_url", "video_url": {"url": to_data_url(data, mime)}}


def audio_part(data: bytes, mime: str) -> dict[str, Any]:
    return {"type": "audio_url", "audio_url": {"url": to_data_url(data, mime)}}


class NvidiaError(RuntimeError):
    """Error normalizado de la API de NVIDIA."""


class NvidiaClient:
    """Envoltura async sobre la API OpenAI-compatible de NVIDIA NIM."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.nvidia_api_key or "not-configured",
            base_url=settings.nvidia_base_url,
            timeout=httpx.Timeout(300.0, connect=30.0),
            max_retries=0,
        )
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0))

    async def aclose(self) -> None:
        await self._client.close()
        await self._http.aclose()

    # ------------------------------------------------------------------ texto

    def _build_body(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        stream: bool,
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int | None,
        thinking: bool | None,
        extra_body: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Separa los parametros del SDK de los que van en extra_body.

        El cliente de OpenAI rechaza kwargs desconocidos, asi que top_k y
        chat_template_kwargs tienen que viajar dentro de extra_body.
        """
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }
        extra: dict[str, Any] = {}
        if top_k is not None:
            extra["top_k"] = top_k
        if thinking is not None:
            extra["chat_template_kwargs"] = {"enable_thinking": thinking}
        if extra_body:
            extra.update(extra_body)
        return body, extra

    async def _with_retry(self, coro_factory, *, what: str):
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await coro_factory()
            except Exception as exc:  # noqa: BLE001 - se reintenta y se normaliza
                status = getattr(exc, "status_code", None)
                if status is not None and status not in RETRYABLE_STATUS:
                    raise NvidiaError(f"{what} fallo ({status}): {exc}") from exc
                last_exc = exc
                delay = BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    "%s fallo (intento %d/%d), reintento en %.1fs: %s",
                    what,
                    attempt + 1,
                    MAX_RETRIES,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
        raise NvidiaError(f"{what} fallo tras {MAX_RETRIES} intentos: {last_exc}")

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.6,
        top_p: float = 0.95,
        top_k: int | None = None,
        thinking: bool | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        body, extra = self._build_body(
            model,
            messages,
            stream=True,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            thinking=thinking,
            extra_body=extra_body,
        )
        try:
            stream = await self._client.chat.completions.create(**body, extra_body=extra or None)
            async for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning", None) or getattr(
                    delta, "reasoning_content", None
                )
                if reasoning:
                    yield {"type": "reasoning", "delta": reasoning}
                if delta.content:
                    yield {"type": "delta", "delta": delta.content}
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status_code", None)
            raise NvidiaError(f"Streaming con {model} fallo ({status}): {exc}") from exc
        yield {"type": "done"}

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.6,
        top_p: float = 0.95,
        top_k: int | None = None,
        thinking: bool | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Devuelve (razonamiento, contenido) de una completación no streaming."""
        body, extra = self._build_body(
            model,
            messages,
            stream=False,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            thinking=thinking,
            extra_body=extra_body,
        )

        async def call():
            return await self._client.chat.completions.create(**body, extra_body=extra or None)

        response = await self._with_retry(call, what=f"Completacion con {model}")
        message = response.choices[0].message
        reasoning = (
            getattr(message, "reasoning", None)
            or getattr(message, "reasoning_content", None)
            or ""
        )
        return reasoning, message.content or ""

    # ------------------------------------------------------------- embeddings

    async def embed(self, model: str, texts: Sequence[str]) -> list[list[float]]:
        async def call():
            return await self._client.embeddings.create(model=model, input=list(texts))

        response = await self._with_retry(call, what=f"Embeddings con {model}")
        return [item.embedding for item in response.data]

    # ------------------------------------------------------------------- voz

    async def transcribe(
        self, model: str, audio: bytes, filename: str
    ) -> tuple[str, str | None]:
        """Transcribe audio. Devuelve (texto, duracion_s) o lanza NvidiaError."""
        url = f"{self.settings.nvidia_base_url.rstrip('/')}{self.settings.nvidia_asr_path}"
        files = {"file": (filename, audio, guess_mime(filename, "audio/wav"))}
        data = {"language": "es", "model": model}
        try:
            response = await self._http.post(url, files=files, data=data)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise NvidiaError(
                f"ASR fallo ({exc.response.status_code}) en {self.settings.nvidia_asr_path}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise NvidiaError(f"ASR no se pudo conectar: {exc}") from exc

        try:
            payload = response.json()
        except ValueError:
            return response.text.strip(), None

        text = ""
        duration: str | None = None
        if isinstance(payload, dict):
            text = payload.get("text") or ""
            duration = payload.get("duration")
        elif isinstance(payload, str):
            text = payload
        return text.strip(), duration

    async def speak(
        self, model: str, text: str, *, voice: str | None = None, language: str = "es"
    ) -> bytes:
        url = f"{self.settings.nvidia_base_url.rstrip('/')}{self.settings.nvidia_tts_path}"
        body: dict[str, Any] = {"model": model, "text": text, "language": language}
        if voice:
            body["voice"] = voice
        try:
            response = await self._http.post(url, json=body)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise NvidiaError(
                f"TTS fallo ({exc.response.status_code}) en {self.settings.nvidia_tts_path}: {detail}"
            ) from exc
        except httpx.HTTPError as exc:
            raise NvidiaError(f"TTS no se pudo conectar: {exc}") from exc
        return response.content

    # ----------------------------------------------------------------- probe

    async def probe(self, model: str, *, prompt: str = "ping") -> tuple[bool, str]:
        try:
            _, text = await self.complete(
                model,
                [{"role": "user", "content": prompt}],
                max_tokens=8,
                temperature=0.0,
                thinking=False,
            )
            return True, (text or "").strip()[:80] or "sin respuesta"
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)[:200]
