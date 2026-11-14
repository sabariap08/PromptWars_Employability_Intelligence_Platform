"""Shared agent base class."""
import json

from flask import current_app


class BaseAgent:
    name = "base"
    label = "Base agent"

    def __init__(self):
        self.ai = current_app.extensions.get("ai_manager")

    def run(self, state: dict) -> dict:
        raise NotImplementedError

    def ai_text(self, prompt: str, system: str, fallback: str) -> dict:
        if not self.ai:
            return {"text": fallback, "provider": "deterministic-fallback", "model": "rules", "_ai": False}
        response = self.ai.generate_text(prompt, system=system, fallback_text=fallback)
        return {
            "text": response.get("text") or fallback,
            "provider": response.get("provider", "deterministic-fallback"),
            "model": response.get("model", "rules"),
            "_ai": bool(response.get("ok")),
        }

    @staticmethod
    def json_safe(value) -> str:
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            return str(value)
