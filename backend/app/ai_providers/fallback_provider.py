"""Deterministic fallback used when no provider is available."""


class FallbackProvider:
    name = "deterministic-fallback"
    label = "Deterministic rules"

    def __init__(self, fallback_text: str = ""):
        self.fallback_text = fallback_text

    def generate(self):
        return {"text": self.fallback_text, "provider": self.name, "model": "rules"}
