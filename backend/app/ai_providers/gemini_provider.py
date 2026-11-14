"""Google Gemini adapter (generateContent API)."""
import requests

from app.ai_providers.base_provider import AIProviderError, BaseProvider


class GeminiProvider(BaseProvider):
    name = "gemini"
    label = "Google Gemini"

    def is_configured(self) -> bool:
        return bool(self.app.config.get("GEMINI_API_KEY"))

    def model(self) -> str:
        return self.app.config.get("GEMINI_MODEL", "gemini-1.5-flash")

    def generate(self, prompt, system=None, temperature=0.2):
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model()}:generateContent"
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            response = requests.post(
                url,
                params={"key": self.app.config["GEMINI_API_KEY"]},
                json=payload,
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise AIProviderError("Gemini timed out.") from exc
        except requests.RequestException as exc:
            raise AIProviderError("Gemini is unreachable.") from exc
        if response.status_code == 429:
            raise AIProviderError("Gemini rate limit reached.")
        if response.status_code in {400, 401, 403}:
            raise AIProviderError("Gemini rejected the API key or request.")
        if response.status_code >= 400:
            raise AIProviderError(f"Gemini returned HTTP {response.status_code}.")
        try:
            data = response.json()
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise AIProviderError("Gemini returned an unexpected response.") from exc
        return {"text": text, "provider": self.name, "model": self.model()}
