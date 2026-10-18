# app/interfaces/http/whatsapp_router.py
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request

from app.domain.models.conversation import ConversationState

router = APIRouter()
_GRAPH = None  # inyectado desde main


def set_graph(graph) -> None:
    global _GRAPH
    _GRAPH = graph


@router.get("/webhooks/whatsapp")
async def verify(
    hub_mode: str | None = None,
    hub_challenge: str | None = None,
    hub_verify_token: str | None = None,
):
    if hub_challenge:
        print(f"[WHATSAPP VERIFY] challenge={hub_challenge}")
        return int(hub_challenge)
    return {"status": "ok"}


@router.post("/webhooks/whatsapp")
async def incoming(request: Request):
    # 1) LOG raw
    raw = await request.body()
    try:
        raw_txt = raw.decode("utf-8", "ignore")
    except Exception:
        raw_txt = str(raw)
    print("[WHATSAPP RAW]", raw_txt)

    # 2) Parse JSON
    try:
        payload = json.loads(raw_txt)
    except Exception as e:
        print("[WHATSAPP JSON ERROR]", repr(e))
        return {
            "status": "ignored",
            "reason": "bad_json",
            "debug": {"raw_sample": raw_txt[:500]},
        }

    # 3) Extraer
    from_id, text, phone_number_id = _extract(payload)
    print(f"[WHATSAPP PARSED] from={from_id!r} text={text!r} phone={phone_number_id!r}")

    if not (from_id and text):
        # Devuelve DEBUG útil en la respuesta
        debug = {
            "top_keys": (
                list(payload.keys())
                if isinstance(payload, dict)
                else str(type(payload))
            ),
            "entry_type": (
                type(
                    payload.get("entry") if isinstance(payload, dict) else None
                ).__name__
                if isinstance(payload, dict)
                else None
            ),
            "has_toplevel_messages": (
                isinstance(
                    payload.get("messages") if isinstance(payload, dict) else None, list
                )
                if isinstance(payload, dict)
                else False
            ),
            "entry_sample": (
                (payload.get("entry") or [])[:1] if isinstance(payload, dict) else None
            ),
            "raw_sample": raw_txt[:500],
        }
        print("[WHATSAPP NO_MESSAGE DEBUG]", debug)
        return {"status": "ignored", "reason": "no_message", "debug": debug}

    if _GRAPH is None:
        print("[WHATSAPP] No graph injected")
        return {"status": "error", "reason": "no_graph"}

    # 4) Invoca grafo
    state: ConversationState = {
        "user_id": f"wa:{from_id}",
        "input_text": text,
        "history": [],
    }
    try:
        result = _GRAPH.invoke(state)
        reply = result.get("output_text") or "(sin respuesta)"
        print(f"[WHATSAPP REPLY] {reply[:180]}")
    except Exception as e:
        print("[WHATSAPP GRAPH ERROR]", repr(e))
        return {"status": "error", "reason": "graph_exception"}

    # En local, simulamos envío y devolvemos la respuesta
    return {"status": "simulated", "reply": reply}


def _extract(payload: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    """
    Devuelve (from_id, text, phone_number_id). Soporta:
    - entry -> changes -> value -> messages  (estándar Meta)
    - top-level messages (útil para pruebas locales)
    """
    try:
        # Caso estándar Meta
        entries = payload.get("entry") or []
        if isinstance(entries, list):
            for entry in entries:
                changes = (entry or {}).get("changes") or []
                for ch in changes:
                    value = (ch or {}).get("value") or {}
                    phone_number_id = (value.get("metadata") or {}).get(
                        "phone_number_id"
                    )
                    messages = value.get("messages") or []
                    found = _extract_from_messages(messages)
                    if found:
                        from_id, text = found
                        return from_id, text, phone_number_id

        # Fallback: top-level messages
        if isinstance(payload.get("messages"), list):
            msgs = payload["messages"]
            found = _extract_from_messages(msgs)
            if found:
                from_id, text = found
                return from_id, text, None

        # Nada encontrado
        return None, None, None
    except Exception as e:
        print("[WHATSAPP EXTRACT ERROR]", repr(e))
        return None, None, None


def _extract_from_messages(
    messages: list[dict[str, Any]]
) -> tuple[str | None, str | None] | None:
    for msg in messages:
        from_id = msg.get("from") or msg.get("wa_id")
        text = None

        # tipo text
        if isinstance(msg.get("text"), dict):
            text = msg["text"].get("body")

        # botones / interactivos
        if not text and msg.get("type") == "button":
            text = (msg.get("button") or {}).get("text")
        if not text and msg.get("type") == "interactive":
            inter = msg.get("interactive") or {}
            text = (inter.get("list_reply") or {}).get("title") or (
                inter.get("button_reply") or {}
            ).get("title")

        # fallbacks
        if not text:
            text = msg.get("body") or msg.get("message") or msg.get("caption")

        if from_id and text:
            return from_id, text

    return None
