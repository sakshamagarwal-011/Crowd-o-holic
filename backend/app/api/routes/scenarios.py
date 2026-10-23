from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.ai_service import get_ai_provider
from app.ai.schemas import ScenarioParseResult

router = APIRouter(prefix="/api/scenarios", tags=["Scenarios"])


class ParseRequest(BaseModel):
    text: str


@router.post("/parse", response_model=ScenarioParseResult)
async def parse_scenario(req: ParseRequest) -> ScenarioParseResult:
    """
    Parse a natural language scenario description using AI (Qwen or mock).
    Returns structured scenario parameters validated by Pydantic.
    """
    provider = get_ai_provider()
    result = await provider.parse_scenario(req.text)
    return result
