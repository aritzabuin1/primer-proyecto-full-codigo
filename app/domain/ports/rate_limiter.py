from abc import ABC, abstractmethod


class RateLimiterPort(ABC):
    @abstractmethod
    def allow(self, user_id: str, key: str, limit: int, per_seconds: int) -> bool: ...
