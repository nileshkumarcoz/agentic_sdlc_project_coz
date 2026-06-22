"""FastAPI router for Story 109061 — story generation endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.agents.story_generator_agent import StoryGeneratorAgent, UserStory

router = APIRouter(prefix="/api/v1/stories", tags=["story-generator"])


class UserStoryOut(BaseModel):
    title: str
    description: str
    acceptance_criteria: List[str]
    priority: str
    points: int

    @classmethod
    def from_domain(cls, s: UserStory) -> "UserStoryOut":
        return cls(
            title=s.title,
            description=s.description,
            acceptance_criteria=s.acceptance_criteria,
            priority=s.priority,
            points=s.points,
        )


class GenerateResponse(BaseModel):
    stories: List[UserStoryOut]


_agent: StoryGeneratorAgent | None = None


def _get_agent() -> StoryGeneratorAgent:
    global _agent
    if _agent is None:
        _agent = StoryGeneratorAgent()
    return _agent


@router.post("/generate", response_model=GenerateResponse)
async def generate_stories(file: UploadFile = File(...)) -> GenerateResponse:
    """Upload a requirements document and receive generated user stories."""
    allowed = {"text/plain", "text/markdown"}
    if file.content_type not in allowed and not (
        file.filename or ""
    ).lower().endswith((".txt", ".md")):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Allowed: TXT, MD (PoC).",
        )
    content = await file.read()
    try:
        agent = _get_agent()
        stories = agent.run(content, filename=file.filename or "requirements.txt")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:  # LLM / network errors
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")
    return GenerateResponse(stories=[UserStoryOut.from_domain(s) for s in stories])
