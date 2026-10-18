from typing import Literal, TypedDict

Role = Literal["user", "assistant", "system"]


class Message(TypedDict):
    role: Role
    content: str


class ConversationRecord(TypedDict, total=False):
    user_id: str
    history: list[Message]
    updated_at: float  # nombre estandarizado (snake_case)


# Estado que viaja por el grafo
class ConversationState(TypedDict, total=False):
    user_id: str
    input_text: str
    output_text: str
    history: list[Message]  # memoria corta que cargamos en el grafo
    rejected: bool  # p.ej. por throttle / moderation
    context_docs: list[str]  # RAG opcional
