import time

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection

from app.domain.models.conversation import ConversationRecord, Message
from app.domain.ports.conversation_repo import ConversationRepoPort


class MongoConversationRepo(ConversationRepoPort):
    def __init__(self, uri: str, db_name: str, collection: str = "conversations"):
        # timeouts cortos para no colgar el arranque
        self._client = MongoClient(
            uri, serverSelectionTimeoutMS=1500, connectTimeoutMS=1500
        )
        self._db = self._client[db_name]
        self._col: Collection = self._db[collection]
        self._col.create_index([("user_id", ASCENDING)], unique=True)

    def get(self, user_id: str) -> ConversationRecord | None:
        doc = self._col.find_one({"user_id": user_id}, projection={"_id": False})
        return doc or None

    def upsert(self, user_id: str, history: list[Message]) -> None:
        self._col.update_one(
            {"user_id": user_id},
            {"$set": {"history": history, "updated_at": time.time()}},
            upsert=True,
        )

    def append_and_trim(
        self, user_id: str, message: Message, max_len: int = 20
    ) -> None:
        # push + slice atómico
        self._col.update_one(
            {"user_id": user_id},
            {
                "$push": {"history": {"$each": [message], "$slice": -max_len}},
                "$set": {"updated_at": time.time()},
                "$setOnInsert": {"user_id": user_id},
            },
            upsert=True,
        )
