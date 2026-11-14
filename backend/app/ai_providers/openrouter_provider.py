"""OpenRouter (OpenAI-compatible) adapter."""
from app.ai_providers.base_provider import BaseProvider, openai_style_chat


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    label = "OpenRouter"

    def is_configured(self) -> bool:
        return bool(self.app.config.get("OPENROUTER_API_KEY"))

    def model(self) -> str:
        return self.app.config.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct")

    def generate(self, prompt, system=None, temperature=0.2):
        response = openai_style_chat(
            "https://openrouter.ai/api/v1/chat/completions",
            {
                "Authorization": f"Bearer {self.app.config['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://eip.local",
                "X-Title": "Employability Intelligence Platform",
            },
            self.model(),
            prompt,
            system,
            temperature,
            self.timeout,
        )
        response["provider"] = self.name
        return response
