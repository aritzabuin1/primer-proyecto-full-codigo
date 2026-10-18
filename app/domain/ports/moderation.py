from abc import ABC, abstractmethod

from app.domain.models.policy import ModerationResult, PolicyConfig


class ModerationPort(ABC):
    @abstractmethod
    def check(self, text: str, policy: PolicyConfig) -> ModerationResult: ...
