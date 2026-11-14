"""Common interface for all AI providers. Keys live only in server config."""
import json
import re

import requests


class AIProviderError(Exception):
    """Raised for provider failures with a safe, non-secret message."""


def extract_json(text: str):
    """Parse JSON from a model response, tolerating code fences."""
    if not text:
        raise ValueError("empty response")
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(cleaned[start : end + 1])


def openai_style_chat(url, headers, model, prompt, system=None, temperature=0.2, timeout=25, extra=None) -> dict:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": model, "messages": messages, "temperature": temperature}
    if extra:
        payload.update(extra)
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.Timeout as exc:
        raise AIProviderError("Provider timed out.") from exc
    except requests.RequestException as exc:
        raise AIProviderError("Provider is unreachable.") from exc
    if response.status_code == 429:
        raise AIProviderError("Provider rate limit reached.")
    if response.status_code in {401, 403}:
        raise AIProviderError("Provider rejected the API key.")
    if response.status_code >= 400:
        raise AIProviderError(f"Provider returned HTTP {response.status_code}.")
    try:
        data = response.json()
        text = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("Provider returned an unexpected response.") from exc
    return {"text": text, "model": model}


class BaseProvider:
    name = "base"
    label = "Base provider"

    def __init__(self, app):
        self.app = app
        self.timeout = app.config.get("AI_TIMEOUT_SECONDS", 25)

    def is_configured(self) -> bool:
        return False

    def model(self) -> str:
        return ""

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.2) -> dict:
        raise NotImplementedError

    def health(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "configured": self.is_configured(),
            "model": self.model(),
            "status": "configured" if self.is_configured() else "not_configured",
        }
