# app/interfaces/http/chat_router.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/v1", tags=["chat"])


class ChatRequest(BaseModel):
    user_id: str | None = None
    text: str


class ChatResponse(BaseModel):
    reply: str
    rejected: bool = False


class MemoryResponse(BaseModel):
    user_id: str
    history: list[dict[str, Any]]


@router.post("/chat", response_model=ChatResponse)
async def chat(req: Request, body: ChatRequest) -> ChatResponse:
    graph = getattr(req.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=500, detail="Graph no inicializado")
    user_id = body.user_id or "anon"
    try:
        result = graph.invoke({"user_id": user_id, "input_text": body.text})
        return ChatResponse(
            reply=result.get("output_text", ""),
            rejected=bool(result.get("rejected", False)),
        )
    except Exception as e:
        print(f"[API ERROR] /v1/chat: {e}")
        raise HTTPException(status_code=500, detail="Error generando respuesta") from e


@router.get("/memory", response_model=MemoryResponse)
async def memory(req: Request, user_id: str) -> MemoryResponse:
    repo = getattr(req.app.state, "repo", None)
    if repo is None:
        raise HTTPException(status_code=500, detail="Repo no inicializado")
    rec = repo.get(user_id)
    history: list[dict[str, Any]] = rec["history"] if rec else []
    return MemoryResponse(user_id=user_id, history=history)


@router.post("/reset", response_model=MemoryResponse)
async def reset(req: Request, body: ChatRequest) -> MemoryResponse:
    repo = getattr(req.app.state, "repo", None)
    if repo is None:
        raise HTTPException(status_code=500, detail="Repo no inicialidado")
    user_id = body.user_id or "anon"
    repo.upsert(user_id, [])
    return MemoryResponse(user_id=user_id, history=[])
