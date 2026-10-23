from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from app.services.tinyfish_service import (
    TinyFishRequestError,
    TinyFishUnavailableError,
    fetch_public_sources,
    search_public_sources,
)

router = APIRouter(prefix="/api/intelligence", tags=["Live Intelligence"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=300)


class SourceResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    site_name: str = ""


class SearchResponse(BaseModel):
    query: str
    results: list[SourceResult]
    disclaimer: str = "Public-source context only; verify with venue operators and official agencies."


class FetchRequest(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=3)


class FetchedSource(BaseModel):
    title: str
    url: str
    text: str


def _raise_service_error(exc: Exception) -> None:
    if isinstance(exc, TinyFishUnavailableError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/search", response_model=SearchResponse)
async def search_intelligence(req: SearchRequest) -> SearchResponse:
    """Search public safety/transport/event sources at an operator's request."""
    try:
        results = await search_public_sources(req.query.strip())
    except (TinyFishUnavailableError, TinyFishRequestError) as exc:
        _raise_service_error(exc)
    return SearchResponse(query=req.query.strip(), results=results)


@router.post("/fetch", response_model=list[FetchedSource])
async def fetch_intelligence(req: FetchRequest) -> list[FetchedSource]:
    """Read selected public sources as clean text for the safety desk."""
    try:
        result = await fetch_public_sources([str(url) for url in req.urls])
    except (TinyFishUnavailableError, TinyFishRequestError) as exc:
        _raise_service_error(exc)
    return [FetchedSource(**item) for item in result]
