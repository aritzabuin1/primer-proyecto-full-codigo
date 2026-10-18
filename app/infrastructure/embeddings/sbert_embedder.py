from __future__ import annotations

from sentence_transformers import SentenceTransformer


class SBertEmbedder:
    def __init__(
        self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ) -> None:
        self._model = SentenceTransformer(model_name)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        arr = self._model.encode(
            texts,
            batch_size=32,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        # numpy -> listas de Python
        return [v.tolist() for v in arr]

    def embed_one(self, text: str) -> list[float]:
        # Reutiliza la versión por lotes para mantener una única implementación
        return self.embed_batch([text])[0]
