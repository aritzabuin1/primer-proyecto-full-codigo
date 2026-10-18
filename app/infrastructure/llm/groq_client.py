import os

from app.domain.ports.llm import LLMPort

try:
    from groq import Groq
except Exception:  # paquete no instalado en algunos entornos
    Groq = None  # type: ignore


class GroqLLM(LLMPort):
    def __init__(
        self, api_key: str | None = None, model: str | None = None, timeout: int = 40
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        if Groq is None:
            raise RuntimeError("Paquete 'groq' no instalado")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY no configurada")
        self._client = Groq(api_key=self.api_key, timeout=timeout)

    def chat(self, messages: list[dict], **kwargs) -> str:
        mapped = [{"role": m["role"], "content": m["content"]} for m in messages]
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=mapped,
            temperature=kwargs.get("temperature", 0.4),
            max_tokens=kwargs.get("max_tokens", 512),
        )
        return resp.choices[0].message.content or ""
