from abc import ABC, abstractmethod

from app.domain.models.conversation import ConversationRecord, Message


class ConversationRepoPort(ABC):
    @abstractmethod
    def get(self, user_id: str) -> ConversationRecord | None: ...

    @abstractmethod
    def upsert(self, user_id: str, history: list[Message]) -> None: ...

    # útil para truncar historial sin exponer detalles de infra
    @abstractmethod
    def append_and_trim(
        self, user_id: str, message: Message, max_len: int = 20
    ) -> None: ...
