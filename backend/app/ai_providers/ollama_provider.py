"""Local Ollama adapter."""
import requests

from app.ai_providers.base_provider import AIProviderError, BaseProvider


class OllamaProvider(BaseProvider):
    name = "ollama"
    label = "Ollama (local)"

    def host(self) -> str:
        return self.app.config.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.app.config.get("OLLAMA_ENABLED"))

    def model(self) -> str:
        return self.app.config.get("OLLAMA_MODEL", "llama3.1")

    def headers(self) -> dict:
        key = (self.app.config.get("OLLAMA_API_KEY") or "").strip()
        return {"Authorization": f"Bearer {key}"} if key else {}

    def generate(self, prompt, system=None, temperature=0.2):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            response = requests.post(
                f"{self.host()}/api/chat",
                headers={**self.headers(), "Content-Type": "application/json"},
                json={"model": self.model(), "messages": messages, "stream": False, "options": {"temperature": temperature}},
                timeout=self.timeout,
            )
        except requests.Timeout as exc:
            raise AIProviderError("Ollama timed out.") from exc
        except requests.RequestException as exc:
            raise AIProviderError("Ollama is unreachable. Is it running locally?") from exc
        if response.status_code == 402:
            raise AIProviderError("Ollama Cloud requires usage credits or a subscription.")
        if response.status_code in {401, 403}:
            raise AIProviderError("Ollama rejected the API key.")
        if response.status_code >= 400:
            raise AIProviderError(f"Ollama returned HTTP {response.status_code}.")
        try:
            text = response.json()["message"]["content"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AIProviderError("Ollama returned an unexpected response.") from exc
        return {"text": text, "provider": self.name, "model": self.model()}

    def health(self) -> dict:
        base = super().health()
        if not self.is_configured():
            return base
        try:
            response = requests.get(f"{self.host()}/api/tags", headers=self.headers(), timeout=3)
            base["status"] = "reachable" if response.status_code == 200 else f"http_{response.status_code}"
        except requests.RequestException:
            base["status"] = "unreachable"
        return base
