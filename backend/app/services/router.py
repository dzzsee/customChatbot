from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.config import Settings
from app.schemas import ModelInfo


@dataclass(slots=True)
class TaskSpec:
    """Perfil de inferencia para un tipo de tarea."""

    model: str
    thinking: bool = False
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int | None = None
    max_tokens: int = 4096
    extra_body: dict[str, Any] = field(default_factory=dict)


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def text(self, override: str | None = None, *, reasoning: bool | None = None) -> TaskSpec:
        model = override or self.settings.model_text_default
        thinking = (
            reasoning
            if reasoning is not None
            else model != self.settings.model_text_fast
        )
        return TaskSpec(
            model=model,
            thinking=thinking,
            temperature=0.6 if thinking else 0.2,
            top_p=0.95,
            top_k=None if thinking else 1,
            max_tokens=8192 if thinking else 4096,
        )

    def image(self, *, reasoning: bool = False) -> TaskSpec:
        return TaskSpec(
            model=self.settings.model_omni,
            thinking=reasoning,
            temperature=0.6 if reasoning else 0.2,
            top_p=0.95,
            top_k=None if reasoning else 1,
            max_tokens=8192 if reasoning else 3072,
        )

    def video(self) -> TaskSpec:
        return TaskSpec(
            model=self.settings.model_omni,
            thinking=True,
            temperature=0.6,
            top_p=0.95,
            max_tokens=8192,
            extra_body={"mm_processor_kwargs": {"use_audio_in_video": True}},
        )

    def document_images(self) -> TaskSpec:
        return TaskSpec(
            model=self.settings.model_omni,
            thinking=False,
            temperature=0.2,
            top_p=0.95,
            top_k=1,
            max_tokens=4096,
        )

    def ocr(self) -> TaskSpec:
        return TaskSpec(
            model=self.settings.model_ocr,
            thinking=False,
            temperature=0.1,
            top_p=0.95,
            top_k=1,
            max_tokens=4096,
        )

    def asr(self) -> str:
        return self.settings.model_asr

    def tts(self) -> str:
        return self.settings.model_tts

    def embed(self) -> str:
        return self.settings.model_embed

    def safety(self) -> str:
        return self.settings.model_safety

    def for_ui(self) -> list[ModelInfo]:
        return [
            ModelInfo(
                id=self.settings.model_text_default,
                label="DeepSeek V4.1 Flash",
                role="text",
                description="Respuesta muy rapida para preguntas cortas y tareas diarias.",
            ),
            ModelInfo(
                id=self.settings.model_text_premium,
                label="Nemotron 3 Ultra 550B",
                role="text",
                description="Razonamiento de maxima calidad. Mas lento y mas caro.",
            ),
            ModelInfo(
                id=self.settings.model_text_lightning,
                label="Nemotron 3.5 Lightning 30B",
                role="text",
                description="Respuesta rapida y economica. Ideal para RAG.",
            ),
            ModelInfo(
                id="nvidia/nemotron-3-super-120b-a12b",
                label="Nemotron 3 Super 120B",
                role="text",
                description="Equilibrio entre calidad y razonamiento.",
            ),
            ModelInfo(
                id=self.settings.model_omni,
                label="Nemotron 3 Nano Omni 30B",
                role="omni",
                description="Imagen, video, voz y texto. Solo se usa para analisis de medios.",
            ),
        ]
