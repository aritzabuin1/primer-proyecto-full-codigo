import time

from app.domain.models.conversation import ConversationRecord, Message
from app.domain.ports.conversation_repo import ConversationRepoPort


class InMemoryConversationRepo(ConversationRepoPort):
    def __init__(self):
        self._store: dict[str, ConversationRecord] = {}

    def get(self, user_id: str) -> ConversationRecord | None:
        return self._store.get(user_id)

    def upsert(self, user_id: str, history: list[Message]) -> None:
        self._store[user_id] = {
            "user_id": user_id,
            "history": history,
            "updated_at": time.time(),
        }

    def append_and_trim(
        self, user_id: str, message: Message, max_len: int = 20
    ) -> None:
        rec = self.get(user_id) or {"user_id": user_id, "history": []}
        hist = rec.get("history", [])
        hist.append(message)
        if len(hist) > max_len:
            hist = hist[-max_len:]
        rec["history"] = hist
        rec["updated_at"] = time.time()
        self._store[user_id] = rec
