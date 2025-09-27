from abc import ABC, abstractmethod


class RetrieverPort(ABC):
    @abstractmethod
    def search(self, query: str, k: int = 4) -> list[str]: ...
