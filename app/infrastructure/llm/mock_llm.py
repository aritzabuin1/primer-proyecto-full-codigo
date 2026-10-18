from app.domain.ports.llm import LLMPort


class MockLLM(LLMPort):
    def chat(self, messages: list[dict], **kwargs) -> str:
        # últimas 1-2 entradas para simular contexto
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        if not last_user:
            return "Hola, soy un LLM simulado. ¿En qué te ayudo?"
        return f"(mock) Me has dicho: {last_user[:200]}"
