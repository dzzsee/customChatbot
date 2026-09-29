from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class FileKind(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"


class ChatMessageIn(BaseModel):
    role: MessageRole
    content: str
    attachment_ids: list[str] = Field(default_factory=list)
    model: str | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn]
    model: str | None = Field(
        default=None,
        description="Override del modelo de texto. None usa MODEL_TEXT_DEFAULT.",
    )
    attachment_ids: list[str] = Field(
        default_factory=list,
        description="Archivos a incorporar al contexto de este turno.",
    )
    use_rag: bool = True
    reasoning: bool | None = Field(
        default=None,
        description="Fuerza el modo de razonamiento. None lo decide el router.",
    )
    inline_media: bool | None = Field(
        default=None,
        description=(
            "Reenvia el archivo original al modelo en vez de usar solo su analisis. "
            "None usa imagenes (barato) y no videos (caro)."
        ),
    )
    speak: bool = False


class AttachmentOut(BaseModel):
    file_id: str
    name: str
    mime: str
    kind: FileKind
    size_bytes: int
    duration_s: float | None = None
    width: int | None = None
    height: int | None = None
    page_count: int | None = None
    url: str
    analysis: str
    created_at: datetime


class AnalyzeResponse(BaseModel):
    attachment: AttachmentOut
    analysis: str
    warnings: list[str] = Field(default_factory=list)


class TranscribeResponse(BaseModel):
    text: str
    model: str
    language: str = "es"
    duration_s: float | None = None
    used_fallback: bool = False


class SpeakResponse(BaseModel):
    audio_base64: str
    mime: str = "audio/wav"
    model: str
    voice: str | None = None


class FileListResponse(BaseModel):
    files: list[AttachmentOut]


class KnowledgeHit(BaseModel):
    file_id: str | None = None
    name: str | None = None
    kind: str | None = None
    text: str
    score: float | None = None


class KnowledgeResponse(BaseModel):
    query: str
    hits: list[KnowledgeHit] = Field(default_factory=list)


class ModelInfo(BaseModel):
    id: str
    label: str
    role: str
    description: str


class ModelListResponse(BaseModel):
    models: list[ModelInfo]
    default: str


class ProbeResult(BaseModel):
    model: str
    role: str
    ok: bool
    detail: str


class HealthResponse(BaseModel):
    status: str
    api_key_configured: bool
    base_url: str
    ffmpeg_available: bool
    rag_available: bool
    models: list[ProbeResult] = Field(default_factory=list)
    limits: dict[str, int | float]
