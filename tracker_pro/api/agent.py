from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from tracker_pro.api.auth import get_current_user
from tracker_pro.config import settings
from tracker_pro.database.models import User
from tracker_pro.schemas.agent_schema import AgentChatRequest, AgentChatResponse
from tracker_pro.chain.agent import run_agent


agent_router = APIRouter(prefix="/agent", tags=["AI Assistant"])


@agent_router.post("/chat/", response_model=AgentChatResponse)
def chat(payload: AgentChatRequest, current_user: User = Depends(get_current_user)):
    today = datetime.now(ZoneInfo(settings.app_timezone)).date().isoformat()
    try:
        answer = run_agent(payload.message, current_user.id, today)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI service request failed") from exc
    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(status_code=502, detail="AI service returned an invalid response")
    return AgentChatResponse(answer=answer)
