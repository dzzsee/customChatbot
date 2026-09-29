from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

MANAGED_PREFIXES = (
    "NVIDIA_",
    "MODEL_",
    "MAX_",
    "ENABLE_",
    "RAG_",
    "FILE_",
    "UI_LANGUAGE",
    "DATA_DIR",
    "CORS_ORIGINS",
    "SAFETY_",
)


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Configuracion aislada: directorio temporal, sin llamadas reales a NVIDIA."""
    for key in list(__import__("os").environ):
        if key.isupper() and key.startswith(MANAGED_PREFIXES):
            monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key-not-real")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ENABLE_RAG", "false")
    monkeypatch.setenv("ENABLE_SAFETY", "true")
    monkeypatch.setenv("SAFETY_FAIL_OPEN", "true")
    monkeypatch.setenv("ENABLE_TTS", "true")

    from app.config import get_settings

    get_settings.cache_clear()
    try:
        yield get_settings()
    finally:
        get_settings.cache_clear()


@pytest.fixture
def client(settings):
    """Cliente de la API con el lifespan real (SQLite temporal)."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
