# scripts/ingest_scientists.py
from __future__ import annotations

import os
import re
import time
import uuid

import requests
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

# Usa tu embedder ya existente
from app.infrastructure.embeddings.sbert_embedder import SBertEmbedder

# Config
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "scientists")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

SCIENTISTS = {
    "Albert Einstein": "https://es.wikipedia.org/wiki/Albert_Einstein",
    "Marie Curie": "https://es.wikipedia.org/wiki/Marie_Curie",
    "Isaac Newton": "https://es.wikipedia.org/wiki/Isaac_Newton",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; IngestBot/1.0; +https://example.com/bot)"
}


def clean_text(t: str) -> str:
    t = re.sub(r"\s+", " ", t).strip()
    return t


def chunk_paragraphs(text: str, max_chars: int = 800, overlap: int = 100) -> list[str]:
    """
    Chunking simple por caracteres (robusto y suficiente para demo).
    """
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = end - overlap  # solape
        if start < 0:
            start = 0
    return chunks


def ensure_collection(client: QdrantClient, name: str, dim: int) -> None:
    try:
        client.get_collection(name)
        # si existe, nada que hacer
    except Exception:
        client.recreate_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def main():
    embedder = SBertEmbedder(EMBEDDING_MODEL)
    # dimension probada con un embedding sintético
    dim = len(embedder.embed_one("hola mundo"))

    client = QdrantClient(url=QDRANT_URL)
    ensure_collection(client, COLLECTION, dim)

    total_chunks = 0

    for name, url in SCIENTISTS.items():
        print(f"[INGEST] {name} -> {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"[WARN] No pude descargar {url}: {e}")
            continue

        # OJO: aquí pasamos HTML auténtico, NO la URL:
        soup = BeautifulSoup(resp.text, "html.parser")

        # contenido principal de Wikipedia
        content = soup.find(id="mw-content-text") or soup
        paragraphs = content.select("p")
        text = " ".join(clean_text(p.get_text(" ", strip=True)) for p in paragraphs)
        text = clean_text(text)

        parts = chunk_paragraphs(text, max_chars=800, overlap=100)
        if not parts:
            print(f"[WARN] {name}: 0 chunks")
            continue

        vectors = embedder.embed_batch(parts)

        # upsert en Qdrant
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "text": part,
                    "person": name,
                    "url": url,
                    "domain": "scientists",
                    "chunk": i,
                },
            )
            for i, (part, vec) in enumerate(zip(parts, vectors, strict=False))
        ]

        try:
            client.upsert(collection_name=COLLECTION, points=points)
        except Exception as e:
            print(f"[Qdrant upsert ERROR] {name}: {e}")
            continue

        total_chunks += len(points)

        # peq. pausa educada
        time.sleep(0.5)

    print(f"[INGEST] DONE. Total chunks: {total_chunks}")


if __name__ == "__main__":
    main()
