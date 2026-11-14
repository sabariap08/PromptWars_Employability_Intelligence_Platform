"""Groq (OpenAI-compatible) adapter."""
from app.ai_providers.base_provider import BaseProvider, openai_style_chat


class GroqProvider(BaseProvider):
    name = "groq"
    label = "Groq"

    def is_configured(self) -> bool:
        return bool(self.app.config.get("GROQ_API_KEY"))

    def model(self) -> str:
        return self.app.config.get("GROQ_MODEL", "openai/gpt-oss-20b")

    def generate(self, prompt, system=None, temperature=0.2):
        response = openai_style_chat(
            "https://api.groq.com/openai/v1/chat/completions",
            {"Authorization": f"Bearer {self.app.config['GROQ_API_KEY']}", "Content-Type": "application/json"},
            self.model(),
            prompt,
            system,
            temperature,
            self.timeout,
        )
        response["provider"] = self.name
        return response
