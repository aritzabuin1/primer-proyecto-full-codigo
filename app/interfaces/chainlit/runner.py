# app/interfaces/chainlit/runner.py
import chainlit as cl
from app.application.agent.agent_graph import build_graph
from app.domain.ports.conversation_repo import ConversationRepoPort
from app.domain.ports.llm import LLMPort
from app.domain.ports.rate_limiter import RateLimiterPort
from app.infrastructure.db.memory_conversation_repo import InMemoryConversationRepo
from app.infrastructure.db.mongo_conversation_repo import MongoConversationRepo
from app.infrastructure.embeddings.sbert_embedder import SBertEmbedder
from app.infrastructure.llm.groq_client import GroqLLM
from app.infrastructure.llm.mock_llm import MockLLM
from app.infrastructure.moderation.simple_moderation import SimpleModeration
from app.infrastructure.ratelimit.mongo_rate_limiter import MongoRateLimiter
from app.infrastructure.retriever.qdrant_retriever import QdrantRetriever
from config.settings import settings

print("[BOOT] Iniciando runner Chainlit...")
print(f"[BOOT] MONGO_URI={settings.mongo_uri}  MONGO_DB={settings.mongo_db}")
print(
    f"[BOOT] Limits: max_chars={settings.max_input_chars}, "
    f"rpm={settings.rate_limit_per_min}"
)
print(f"[BOOT] USE_MOCK_LLM={settings.use_mock_llm}")


# ---------- LLM ----------
LLM: LLMPort
if settings.use_mock_llm:
    LLM = MockLLM()
    print("[BOOT] Usando MockLLM (sin llamadas externas)")
else:
    api_key = (
        settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
    )
    LLM = GroqLLM(api_key=api_key)
    print("[BOOT] Usando GroqLLM")


# ---------- Rate limiter permisivo (fallback) ----------
class _PermissiveLimiter(RateLimiterPort):
    def allow(self, user_id: str, key: str, limit: int, per_seconds: int) -> bool:
        return True


# ---------- Repo + RateLimiter ----------
repo: ConversationRepoPort
limiter: RateLimiterPort

if getattr(settings, "use_inmemory_store", False):
    print(
        "[BOOT] USE_INMEMORY_STORE=True -> InMemoryConversationRepo + rate limit permisivo"
    )
    repo = InMemoryConversationRepo()
    limiter = _PermissiveLimiter()
else:
    try:
        repo = MongoConversationRepo(uri=settings.mongo_uri, db_name=settings.mongo_db)
        limiter = MongoRateLimiter(uri=settings.mongo_uri, db_name=settings.mongo_db)
        print("[BOOT] MongoConversationRepo + MongoRateLimiter activos")
    except Exception as e:
        print(
            f"[WARN] Mongo no disponible: {e}\n"
            "[BOOT] Fallback InMemoryConversationRepo + rate limit permisivo."
        )
        repo = InMemoryConversationRepo()
        limiter = _PermissiveLimiter()


# ---------- Moderation ----------
MOD = SimpleModeration(default_banned=[])


# ---------- RAG (opcional) ----------
retriever = None
if getattr(settings, "enable_rag", False):
    try:
        model_name = getattr(
            settings, "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
        )
        embedder = SBertEmbedder(model_name)
        retriever = QdrantRetriever(
            url=settings.qdrant_url,
            collection=getattr(settings, "qdrant_collection", "scientists"),
            embedder=embedder,
            default_filter={"domain": "scientists"},
        )
        print("[BOOT] RAG habilitado con Qdrant.")
    except Exception as e:
        print(f"[WARN] No se pudo iniciar el retriever: {e}. Continuo sin RAG.")
        retriever = None


# ---------- Grafo ----------
GRAPH = build_graph(
    llm=LLM,
    repo=repo,
    moderation=MOD,
    limiter=limiter,
    max_turns=5,  # trimming se hace dentro del nodo persist (no en el repo)
    policy={"max_input_chars": settings.max_input_chars},
    rate_limit_per_min=settings.rate_limit_per_min,
    retriever=retriever,
)
print("[BOOT] Grafo con guard + throttle listo.")


# ---------- Chainlit handlers ----------
@cl.on_chat_start
async def start():
    await cl.Message(content="Guardrails activos ✅. ¿En qué te ayudo?").send()


@cl.on_message
async def on_message(message: cl.Message):
    user_id = cl.user_session.get("id") or cl.context.session.id
    cl.user_session.set("id", user_id)
    print("[DEBUG] on_message user_id=", user_id)
    try:
        result = GRAPH.invoke({"user_id": user_id, "input_text": message.content or ""})
        await cl.Message(content=result.get("output_text", "")).send()
    except Exception as e:
        print(f"[ERROR] on_message: {e}")
        await cl.Message(
            content="He tenido un problema procesando tu mensaje. Inténtalo de nuevo."
        ).send()
