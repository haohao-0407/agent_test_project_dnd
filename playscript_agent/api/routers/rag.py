from __future__ import annotations

from fastapi import APIRouter, HTTPException

from playscript_agent.api.schemas import RagQueryRequest
from playscript_agent.api.services import rag_service


router = APIRouter()


@router.post("/api/rag/query")
def query_rag(request: RagQueryRequest) -> dict:
    try:
        hits = rag_service.search_rules(
            request.query,
            user_id=request.userId,
            k=request.k,
        )
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    return {"chunks": [hit.as_dict() for hit in hits]}
