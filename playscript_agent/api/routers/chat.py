from __future__ import annotations

from fastapi import APIRouter, HTTPException

from playscript_agent.api.schemas import ChatRequest
from playscript_agent.api.services import chat_service


router = APIRouter()


@router.post("/api/chat")
def chat(request: ChatRequest) -> dict:
    try:
        return chat_service.handle_chat(request.message, speaker=request.speaker)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
