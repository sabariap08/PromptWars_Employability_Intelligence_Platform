"""Provider manager with ordered fallback and JSON validation."""
import logging

from app.ai_providers.base_provider import AIProviderError, extract_json
from app.ai_providers.fallback_provider import FallbackProvider
from app.ai_providers.gemini_provider import GeminiProvider
from app.ai_providers.groq_provider import GroqProvider
from app.ai_providers.huggingface_provider import HuggingFaceProvider
from app.ai_providers.ollama_provider import OllamaProvider
from app.ai_providers.openrouter_provider import OpenRouterProvider

logger = logging.getLogger("eip.ai")

PROVIDER_CLASSES = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
    "openrouter": OpenRouterProvider,
    "huggingface": HuggingFaceProvider,
    "ollama": OllamaProvider,
}


class ProviderManager:
    def __init__(self, app, overrides: dict | None = None):
        self.app = app
        self.providers = {name: cls(app) for name, cls in PROVIDER_CLASSES.items()}
        self.last_errors = {}
        overrides = overrides or {}
        primary = (overrides.get("primary_provider") or app.config.get("AI_PRIMARY_PROVIDER") or "").lower()
        fallback_raw = overrides.get("fallback_order") or app.config.get("AI_FALLBACK_ORDER", "")
        if isinstance(fallback_raw, str):
            fallback = [item.strip().lower() for item in fallback_raw.split(",") if item.strip()]
        else:
            fallback = [str(item).strip().lower() for item in fallback_raw]
        order = [primary] + fallback if primary else fallback
        self.order = []
        for name in order:
            if name in self.providers and name not in self.order:
                self.order.append(name)

    def status(self) -> list:
        statuses = []
        for name, provider in self.providers.items():
            entry = provider.health()
            entry["last_error"] = self.last_errors.get(name, "")
            entry["position"] = self.order.index(name) + 1 if name in self.order else None
            statuses.append(entry)
        statuses.sort(key=lambda item: item["position"] or 99)
        return statuses

    def _chain(self):
        for name in self.order:
            provider = self.providers[name]
            if provider.is_configured():
                yield provider

    def generate_text(self, prompt: str, system: str | None = None, fallback_text: str = "", temperature: float = 0.2) -> dict:
        for provider in self._chain():
            try:
                result = provider.generate(prompt, system=system, temperature=temperature)
                self.last_errors.pop(provider.name, None)
                return {
                    "text": result.get("text", ""),
                    "provider": result.get("provider", provider.name),
                    "model": result.get("model", provider.model()),
                    "ok": bool(result.get("text")),
                }
            except AIProviderError as exc:
                self.last_errors[provider.name] = str(exc)
                logger.warning("AI provider %s failed: %s", provider.name, exc)
            except Exception as exc:  # defensive: never break a learner workflow
                self.last_errors[provider.name] = "Unexpected provider error."
                logger.warning("AI provider %s unexpected error: %s", provider.name, type(exc).__name__)
        fallback = FallbackProvider(fallback_text).generate()
        fallback["ok"] = False
        return fallback

    def generate_json(self, prompt: str, system: str | None = None, fallback: dict | None = None, required_keys=()) -> dict:
        fallback = fallback or {}
        result = self.generate_text(prompt, system=system, fallback_text="")
        text = result.get("text", "")
        if not text:
            return {**fallback, "_provider": "deterministic-fallback", "_model": "rules", "_ai": False}
        try:
            parsed = extract_json(text)
            if required_keys and not all(key in parsed for key in required_keys):
                raise ValueError("missing keys")
            return {**parsed, "_provider": result.get("provider"), "_model": result.get("model"), "_ai": True}
        except (ValueError, TypeError):
            logger.warning("AI response failed JSON validation from provider %s", result.get("provider"))
            return {**fallback, "_provider": "deterministic-fallback", "_model": "rules", "_ai": False}


def build_provider_manager(app, overrides: dict | None = None) -> ProviderManager:
    return ProviderManager(app, overrides)
