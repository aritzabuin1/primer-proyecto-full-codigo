from abc import ABC, abstractmethod
from typing import Any


class LLMPort(ABC):
    @abstractmethod
    def chat(self, messages: list[dict[str, Any]], **kwargs) -> str: ...
