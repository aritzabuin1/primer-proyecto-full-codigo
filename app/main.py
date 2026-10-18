from __future__ import annotations

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.application.agent.agent_graph import build_graph
from app.infrastructure.db.memory_conversation_repo import InMemoryConversationRepo
from app.infrastructure.db.mongo_conversation_repo import MongoConversationRepo
from app.infrastructure.embeddings.sbert_embedder import SBertEmbedder
from app.infrastructure.llm.groq_client import GroqLLM
from app.infrastructure.llm.mock_llm import MockLLM
from app.infrastructure.moderation.simple_moderation import SimpleModeration
from app.infrastructure.ratelimit.mongo_rate_limiter import MongoRateLimiter
from app.infrastructure.retriever.qdrant_retriever import QdrantRetriever
from app.interfaces.http.chat_router import router as chat_router
from app.interfaces.http.whatsapp_router import (
    router as whatsapp_router,
    set_graph as wa_set_graph,
)
from config.logging import setup_logging
from config.settings import settings

setup_logging()
if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.2)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [settings.allow_origins]
        if isinstance(settings.allow_origins, str)
        else settings.allow_origins
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_objects():

    # LLM

    if getattr(settings, "use_mock_lll", False):
        llm = MockLLM()
        print("[API BOOT] MockLLM activo")
    else:
        api_key = (
            settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
        )
        llm = GroqLLM(api_key=api_key, model=getattr(settings, "groq_model", None))
        print("[API BOOT] GroqLLM activo")

    # Repo + RateLimiter

    try:
        repo = MongoConversationRepo(uri=settings.mongo_uri, db_name=settings.mongo_db)
        limiter = MongoRateLimiter(uri=settings.mongo_uri, db_name=settings.mongo_db)
        print("[API BOOT] MongoConversationRepo + MongoRateLimiter OK")
    except Exception as e:
        print(f"[API WARN] Mongo no disponible: {e} -> InMemory")
        repo = InMemoryConversationRepo()

        class _PermissiveLimiter:
            def allow(self, *Args, **kwargs):
                return True

        limiter = _PermissiveLimiter()

    moderation = SimpleModeration(default_banned=[])

    # RAG

    retriever = None
    if getattr(settings, "enable_rag", False):
        embedder = SBertEmbedder(model_name=settings.embedding_model)
        retriever = QdrantRetriever(
            url=settings.qdrant_url,
            collection=getattr(settings, "qdrant_collection", "scientists"),
            embedder=embedder,
            default_filter=None,
        )
        print("[API BOOT] RAG habilitado con Qdrant")

    graph = build_graph(
        llm=llm,
        repo=repo,
        moderation=moderation,
        limiter=limiter,
        max_turns=5,
        policy={"max_input_chars": settings.max_input_chars},
        rate_limit_per_min=settings.rate_limit_per_min,
        retriever=retriever,
    )
    return llm, repo, limiter, moderation, retriever, graph

    # Exponer en app.state (unico sitio que conoce infra)


_llm, _repo, _limiter, _moderation, _retriever, _graph = _build_objects()
app.state.graph = _graph
app.state.repo = _repo

wa_set_graph(_graph)


@app.get("/v1/health")
def health():
    return {"status": "OK"}


app.include_router(chat_router)
app.include_router(whatsapp_router)

# --- DEBUG: imprime todas las rutas registradas al arrancar ---
for r in app.router.routes:
    methods = getattr(r, "methods", set())
    print(f"[ROUTE] {getattr(r, 'path', '')} {','.join(sorted(methods))}")
