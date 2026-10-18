# app/application/agent/agent_graph.py
from __future__ import annotations

import time
from typing import Any, cast

from langgraph.graph import END, StateGraph

from app.domain.models.conversation import ConversationState, Message
from app.domain.models.policy import PolicyConfig
from app.domain.ports.conversation_repo import ConversationRepoPort
from app.domain.ports.llm import LLMPort
from app.domain.ports.moderation import ModerationPort
from app.domain.ports.rate_limiter import RateLimiterPort
from app.domain.ports.retriever import RetrieverPort


def _safe(name: str, fn):
    def _wrap(state: ConversationState) -> ConversationState:
        try:
            return fn(state)
        except Exception as e:  # pragma: no cover
            print(f"[NODE:{name}] ERROR:", repr(e))
            _set(state, "output_text", f"He tenido un problema interno en {name}.")
            _set(state, "rejected", True)
            return state

    return _wrap


def _set(state: ConversationState, key: str, value: Any) -> None:
    """Asignación segura para TypedDict (evita que mypy proteste)."""
    cast(dict, state)[key] = value


def build_graph(
    llm: LLMPort,
    repo: ConversationRepoPort,
    moderation: ModerationPort,
    limiter: RateLimiterPort,
    max_turns: int = 5,
    policy: PolicyConfig | None = None,
    rate_limit_per_min: int = 20,
    retriever: RetrieverPort | None = None,
):
    policy = policy or {"max_input_chars": 2000}

    def guard(state: ConversationState) -> ConversationState:
        user_text = state.get("input_text", "")
        result = moderation.check(user_text, policy)
        if not result["allowed"]:
            _set(state, "output_text", _friendly_moderation_msg(result["reason"]))
            _set(state, "rejected", True)
        return state

    def throttle(state: ConversationState) -> ConversationState:
        if state.get("rejected"):
            return state
        user_id = state.get("user_id", "anon")
        # usa argumentos posicionales para evitar desajustes de nombre
        ok = limiter.allow(user_id, "chat", rate_limit_per_min, 60)
        if not ok:
            _set(
                state,
                "output_text",
                (
                    "Has superado el límite de mensajes por minuto. "
                    "Inténtalo de nuevo en unos segundos."
                ),
            )
            _set(state, "rejected", True)
        return state

    def load_state(state: ConversationState) -> ConversationState:
        if state.get("rejected"):
            return state
        user_id = state.get("user_id", "anon")
        try:
            rec = repo.get(user_id)
            history = []
            if isinstance(rec, dict):
                h = rec.get("history", [])
                if isinstance(h, list):
                    history = h
            # cualquier otra forma inesperada -> history vacía
        except Exception as e:
            print("[NODE:load_state] ERROR repo.get:", repr(e))
            history = []
        state["history"] = history
        return state

    def retrieve(state: ConversationState) -> ConversationState:
        if state.get("rejected"):
            return state
        if retriever is None:
            return state
        q = state.get("input_text", "")
        docs = retriever.search(q, k=4)
        _set(state, "context_docs", docs)
        return state

    def reason(state: ConversationState) -> ConversationState:
        if state.get("rejected"):
            return state

        user_text = state.get("input_text", "")
        history = cast(list[Message], state.get("history", []))

        chat_messages: list[dict[str, str]] = [
            {"role": m["role"], "content": m["content"]} for m in history
        ]

        ctx_docs = state.get("context_docs") or []
        if ctx_docs:
            ctx = "\n\n".join(ctx_docs[:4])
            chat_messages.append(
                {
                    "role": "system",
                    "content": (
                        "Responde en español. Si el contexto es relevante, "
                        "apóyate en él. Si no, responde de forma general. "
                        "CONTEXTO:\n" + ctx
                    ),
                }
            )

        chat_messages.append({"role": "user", "content": user_text})

        try:
            reply = llm.chat(chat_messages)
            _set(state, "output_text", reply)
        except Exception as e:  # pragma: no cover
            print("[LLM ERROR]", repr(e))
            _set(
                state,
                "output_text",
                (
                    "He tenido un problema llamando al modelo. "
                    "Revisa la clave o el modelo."
                ),
            )
        return state

    def save_state(state: ConversationState) -> ConversationState:
        if state.get("rejected"):
            return state

        user_id = state.get("user_id", "anon")
        user_text = state.get("input_text", "")
        assistant_text = state.get("output_text", "")
        now = time.time()

        print(
            "[DEBUG] save_state user_id=%s u='%s' a='%s'"
            % (user_id, user_text[:40], assistant_text[:40])
        )

        # Guarda recortando a max_turns (posicional para cuadrar con la interfaz)
        repo.append_and_trim(
            user_id, {"role": "user", "content": user_text, "ts": now}, max_turns
        )
        repo.append_and_trim(
            user_id,
            {"role": "assistant", "content": assistant_text, "ts": now + 0.001},
            max_turns,
        )
        return state

    graph = StateGraph(ConversationState)
    graph.add_node("guard", _safe("guard", guard))
    graph.add_node("throttle", _safe("throttle", throttle))
    graph.add_node("load_state", _safe("load_state", load_state))
    graph.add_node("retrieve", _safe("retrieve", retrieve))
    graph.add_node("reason", _safe("reason", reason))
    graph.add_node("save_state", _safe("save_state", save_state))

    graph.set_entry_point("guard")
    graph.add_edge("guard", "throttle")
    graph.add_edge("throttle", "load_state")
    graph.add_edge("load_state", "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "save_state")
    graph.add_edge("save_state", END)

    return graph.compile()


def _friendly_moderation_msg(reason: str) -> str:
    if reason.startswith("too_long"):
        lim = reason.split(">")[-1]
        return (
            "Tu mensaje es demasiado largo. "
            f"Por favor, reduce a menos de {lim} caracteres."
        )
    if reason == "empty_input":
        return "Tu mensaje está vacío. ¿Puedes escribir algo más concreto?"
    if reason.startswith("banned_pattern"):
        return "No puedo procesar ese contenido. Reformula de forma segura, por favor."
    return "No puedo procesar ese contenido."
