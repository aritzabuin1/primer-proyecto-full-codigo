# app/infrastructure/retriever/qdrant_retriever.py
from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.domain.ports.retriever import RetrieverPort


class QdrantRetriever(RetrieverPort):
    def __init__(
        self,
        url: str,
        collection: str,
        embedder,
        default_filter: dict[str, Any] | None = None,
    ):
        self.client = QdrantClient(url=url)
        self.collection = collection
        self.embedder = embedder
        self.default_filter = default_filter or None

        # sanity check: la cole existe
        try:
            self.client.get_collection(self.collection)
        except Exception as e:
            # No reventamos aquí: dejamos que el error se vea en retrieve con detalle
            print(f"[QDRANT] WARN get_collection '{self.collection}': {e!r}")

    def search(self, query: str, k: int = 4) -> list[str]:
        # 1) embed
        vector = self.embedder.embed_one(query)
        # qdrant-client quiere list[float]
        if hasattr(vector, "tolist"):
            vector = vector.tolist()

        # 2) filtro (opcional)
        q_filter = None
        if self.default_filter:
            must = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in self.default_filter.items()
            ]
            q_filter = Filter(must=must)

        # 3) búsqueda
        try:
            res = self.client.search(
                collection_name=self.collection,
                query_vector=vector,  # <- IMPORTANTÍSIMO
                query_filter=q_filter,
                limit=int(k),
                with_payload=True,
            )
        except Exception as e:
            print(f"[QDRANT] ERROR search: {e!r}")
            raise

        # 4) recolecta textos
        docs: list[str] = []
        for p in res:
            payload = p.payload or {}
            txt = (
                payload.get("text")
                or payload.get("chunk_text")
                or payload.get("content")
                or str(payload)
            )
            # evita None / vacíos
            if isinstance(txt, str) and txt.strip():
                docs.append(txt)

        return docs
