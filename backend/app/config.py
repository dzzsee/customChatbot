from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_asr_path: str = "/audio/transcriptions"
    nvidia_tts_path: str = "/audio/speech"

    model_text_default: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    model_text_premium: str = "nvidia/nemotron-3-ultra-550b-a55b"
    model_text_fast: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    model_omni: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    model_ocr: str = "nvidia/nemotron-ocr-v2"
    model_asr: str = "nvidia/parakeet-ctc-0.6b-es"
    model_tts: str = "nvidia/chatterbox-multilingual-tts"
    model_embed: str = "nvidia/nemotron-3-embed-1b"
    model_safety: str = "nvidia/llama-guard-4-12b"

    max_image_mb: int = 20
    max_video_mb: int = 100
    max_video_seconds: int = 120
    max_audio_mb: int = 50
    max_audio_seconds: int = 3600
    max_doc_mb: int = 50
    max_doc_pages: int = 40

    ui_language: str = "es"
    enable_safety: bool = True
    safety_fail_open: bool = True
    enable_tts: bool = True
    enable_rag: bool = True
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 100
    rag_top_k: int = 5
    file_ttl_hours: int = 24

    data_dir: Path = BACKEND_DIR / ".data"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,"
        "https://dzzsee.github.io"
    )

    @property
    def data_root(self) -> Path:
        root = self.data_dir if self.data_dir.is_absolute() else BACKEND_DIR / self.data_dir
        root.mkdir(parents=True, exist_ok=True)
        return root

    @property
    def uploads_dir(self) -> Path:
        path = self.data_root / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_dir(self) -> Path:
        path = self.data_root / "chroma"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def db_path(self) -> Path:
        return self.data_root / "chatbot.db"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def has_api_key(self) -> bool:
        return bool(self.nvidia_api_key.strip())

    @property
    def api_key_looks_valid(self) -> bool:
        """Las claves de build.nvidia.com empiezan por nvapi-. Solo es un aviso."""
        return self.nvidia_api_key.strip().startswith("nvapi-")


@lru_cache
def get_settings() -> Settings:
    return Settings()
