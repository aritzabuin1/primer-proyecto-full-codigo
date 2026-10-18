import time

from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from app.domain.ports.rate_limiter import RateLimiterPort


class MongoRateLimiter(RateLimiterPort):
    def __init__(self, uri: str, db_name: str, collection: str = "rate_limits"):
        self._client = MongoClient(
            uri,
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=2000,
        )
        self._client.admin.command("ping")
        self._col: Collection = self._client[db_name][collection]
        self._col.create_index(
            [("user_id", ASCENDING), ("key", ASCENDING)], unique=True
        )

    def allow(self, user_id: str, key: str, limit: int, per_Seconds: int) -> bool:
        """Devuelve True si aún puede consumir cuota en la ventana [now - per_seconds, now]
        Guarda timestamps es un array y limpiar viejos"""

        now = time.time()
        window_start = now - per_Seconds

        try:
            doc = self._col.find_one({"user_id": user_id, "key": key}) or {"events": []}
            events: list[float] = [
                ts for ts in doc.get("events", []) if ts >= window_start
            ]
            if len(events) >= limit:
                return False
            events.append(now)
            self._col.update_one(
                {"user_id": user_id, "key": key},
                {"$set": {"events": events, "updated_at": now}},
                upsert=True,
            )
            return True
        except PyMongoError:
            # En caso de error de BD, por defecto permitimos (fall-open) para no bloquear el sistema;
            # en produccion podrias preferir fail-closed

            return True
