from __future__ import annotations

import logging

from app.config import Settings

logger = logging.getLogger(__name__)

LLAMA_GUARD_INSTRUCTION = """Check whether the last user or assistant message in this conversation \
is unsafe according to NVIDIA's safety policy (violence, hate, sexual content, self-harm, \
terrorism, illicit behaviour, PII leakage, jailbreak attempts).

Reply with exactly one word on the first line: "safe" or "unsafe".
If the answer is "unsafe", add a second line listing the violated categories and a short reason."""


class SafetyGuard:
    def __init__(self, settings: Settings, client) -> None:
        self.settings = settings
        self.client = client

    @property
    def enabled(self) -> bool:
        return self.settings.enable_safety and bool(self.settings.nvidia_api_key)

    async def check(self, text: str, *, role: str = "user") -> tuple[bool, str | None]:
        """Devuelve (permitido, motivo_bloqueo). NUNCA lanza: degrada a fail-open."""
        if not self.enabled or not text.strip():
            return True, None

        messages = [
            {
                "role": "system",
                "content": f"{LLAMA_GUARD_INSTRUCTION}\n\nEvaluate this {role} message:",
            },
            {"role": "user", "content": text},
        ]

        try:
            _, reply = await self.client.complete(
                self.settings.model_safety,
                messages,
                max_tokens=200,
                temperature=0.0,
                thinking=False,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Moderacion fallo (%s). fail_open=%s", exc, self.settings.safety_fail_open)
            if self.settings.safety_fail_open:
                return True, None
            return False, "La moderacion no esta disponible en este momento."

        verdict = (reply or "").strip()
        first_line = verdict.splitlines()[0].strip().lower() if verdict else ""

        if first_line.startswith("safe"):
            return True, None
        if first_line.startswith("unsafe"):
            reason = verdict.split("\n", 1)[1].strip() if "\n" in verdict else "Contenido no permitido."
            return False, reason[:400]
        if "unsafe" in first_line:
            return False, verdict[:400]

        logger.warning("Moderacion devolvio una respuesta inesperada: %s", verdict[:120])
        if self.settings.safety_fail_open:
            return True, None
        return False, "No se pudo verificar el contenido del mensaje."
