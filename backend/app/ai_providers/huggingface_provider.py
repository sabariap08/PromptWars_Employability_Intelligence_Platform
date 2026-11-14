"""Hugging Face Inference Providers (OpenAI-compatible router) adapter."""
from app.ai_providers.base_provider import BaseProvider, openai_style_chat


class HuggingFaceProvider(BaseProvider):
    name = "huggingface"
    label = "Hugging Face Inference Providers"

    def is_configured(self) -> bool:
        return bool(self.app.config.get("HF_API_KEY"))

    def model(self) -> str:
        return self.app.config.get("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

    def generate(self, prompt, system=None, temperature=0.2):
        response = openai_style_chat(
            "https://router.huggingface.co/v1/chat/completions",
            {"Authorization": f"Bearer {self.app.config['HF_API_KEY']}", "Content-Type": "application/json"},
            self.model(),
            prompt,
            system,
            temperature,
            self.timeout,
        )
        response["provider"] = self.name
        return response
