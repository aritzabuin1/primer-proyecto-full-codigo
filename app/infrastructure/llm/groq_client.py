import os
from typing import Any

from app.domain.ports.llm import LLMPort

try:
    from groq import Groq
except Exception:  # tolera falta de lib o API key en dev
    Groq = None


class GroqLLM(LLMPort):
    def __init__(self, api_key: str | None = None, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self._client = Groq(api_key=self.api_key) if (Groq and self.api_key) else None

    def chat(self, messages: list[dict[str, Any]], **kwargs) -> str:
        # Fallback si no hay cliente/clave: eco minimalista
        if self._client is None:
            content = messages[-1]["content"] if messages else ""
            return f"(fallback) Has dicho: {content}"

        completion = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.3),
            max_tokens=kwargs.get("max_tokens", 200),
        )
        return completion.choices[0].message.content or ""
