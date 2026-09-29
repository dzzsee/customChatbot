from __future__ import annotations

import pytest

from app.services import media
from app.services.rag import chunk_text
from app.services.router import ModelRouter
from app.services.safety import SafetyGuard


class TestSniffKind:
    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("foto.PNG", media.FileKind.image),
            ("clip.mp4", media.FileKind.video),
            ("nota.m4a", media.FileKind.audio),
            ("informe.PDF", media.FileKind.document),
            ("datos.csv", media.FileKind.document),
        ],
    )
    def test_detects_by_extension(self, filename: str, expected: media.FileKind) -> None:
        assert media.sniff_kind(filename) is expected

    def test_rejects_unknown_extension(self) -> None:
        with pytest.raises(media.MediaError, match="no soportado"):
            media.sniff_kind("malicioso.exe")


class TestValidateSize:
    def test_rejects_oversized_image(self, settings) -> None:
        oversized = settings.max_image_mb * media.MB + 1
        with pytest.raises(media.MediaError, match="limite es"):
            media.validate_size(media.FileKind.image, oversized, settings)

    def test_accepts_within_limit(self, settings) -> None:
        media.validate_size(media.FileKind.image, 1024, settings)


class TestChunkText:
    def test_splits_long_text(self) -> None:
        chunks = chunk_text("palabra " * 3000, chunk_size=100, overlap=10)
        assert len(chunks) > 1
        assert all(chunk.strip() for chunk in chunks)

    def test_short_text_is_single_chunk(self) -> None:
        assert chunk_text("un solo fragmento", chunk_size=800) == ["un solo fragmento"]

    def test_empty_text_yields_nothing(self) -> None:
        assert chunk_text("   ") == []

    def test_chunks_overlap(self) -> None:
        words = [f"w{i}" for i in range(200)]
        window, step = 45, 30
        first, second = chunk_text(" ".join(words), chunk_size=60, overlap=20)[:2]
        overlap = window - step
        assert first.split()[-overlap:] == second.split()[:overlap]

    def test_ui_lists_text_models_plus_omni(self, settings) -> None:
        infos = ModelRouter(settings).for_ui()
        roles = [info.role for info in infos]
        assert roles.count("text") == 5
        assert roles[-1] == "omni"


class TestModelRouter:
    def test_default_text_model(self, settings) -> None:
        spec = ModelRouter(settings).text()
        assert spec.model == settings.model_text_default
        assert spec.thinking is (spec.model != settings.model_text_fast)

    def test_override_model_disables_thinking_when_requested(self, settings) -> None:
        spec = ModelRouter(settings).text(settings.model_text_fast, reasoning=False)
        assert spec.model == settings.model_text_fast
        assert spec.thinking is False
        assert spec.top_k == 1

    def test_video_enables_audio_track(self, settings) -> None:
        spec = ModelRouter(settings).video()
        assert spec.model == settings.model_omni
        assert spec.extra_body["mm_processor_kwargs"]["use_audio_in_video"] is True


class FakeClient:
    """Cliente minimo que imita la interfaz de NvidiaClient."""

    def __init__(self, reply: str = "safe", error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.calls: list[list[dict]] = []

    async def complete(self, model, messages, **kwargs):
        self.calls.append(messages)
        if self.error:
            raise self.error
        return "", self.reply


class TestSafetyGuard:
    async def test_allows_safe_message(self, settings) -> None:
        allowed, reason = await SafetyGuard(settings, FakeClient("safe")).check("hola que tal")
        assert allowed is True
        assert reason is None

    async def test_blocks_unsafe_message(self, settings) -> None:
        reply = "unsafe\nViolence: describes how to hurt someone"
        allowed, reason = await SafetyGuard(settings, FakeClient(reply)).check("contenido malo")
        assert allowed is False
        assert reason is not None
        assert "Violence" in reason

    async def test_fails_open_on_error(self, settings) -> None:
        guard = SafetyGuard(settings, FakeClient(error=RuntimeError("boom")))
        allowed, _ = await guard.check("hola")
        assert allowed is True

    async def test_fails_closed_when_configured(self, settings) -> None:
        settings.safety_fail_open = False
        guard = SafetyGuard(settings, FakeClient(error=RuntimeError("boom")))
        allowed, reason = await guard.check("hola")
        assert allowed is False
        assert reason is not None

    async def test_disabled_guard_allows_everything(self, settings) -> None:
        settings.enable_safety = False
        assert (await SafetyGuard(settings, FakeClient()).check("x"))[0] is True

    async def test_empty_text_allowed(self, settings) -> None:
        assert (await SafetyGuard(settings, FakeClient()).check(""))[0] is True
