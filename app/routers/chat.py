from openai import AsyncOpenAI, APIError
from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app.dependencies import SessionDep
from app.llm.agent import run_agent
from functools import lru_cache
from app.schemas.chat import ChatIn, ChatOut

router = APIRouter(prefix="/chat")


@lru_cache
def get_openai_client():
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


@router.post("", response_model=ChatOut)
async def chat(body: ChatIn, session: SessionDep, client=Depends(get_openai_client)):
    try:
        return await run_agent(
            client,
            session,
            body.message,
            settings.OPENAI_MODEL,
            settings.AGENT_MAX_STEPS,
        )
    except APIError as e:
        raise HTTPException(502)
