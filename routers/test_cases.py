"""FastAPI router for test case generation and review endpoints.

Routes:
    POST   /api/v1/stories/{story_id}/generate-test-cases
    GET    /api/v1/stories/{story_id}/test-cases
    PATCH  /api/v1/test-cases/{tc_id}
    GET    /api/v1/stories/{story_id}/coverage-report
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["test-cases"])

# ---------------------------------------------------------------------------
# In-memory store (replace with DB session / repository in production)
# ---------------------------------------------------------------------------
_runs: Dict[str, dict] = {}
_test_cases: Dict[str, dict] = {}  # tc_id -> test case dict


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class GenerationOptions(BaseModel):
    include_edge_cases: bool = True
    include_test_data: bool = True
    max_cases_per_ac: int = 10


class GenerateRequest(BaseModel):
    regenerate: bool = False
    options: GenerationOptions = GenerationOptions()


class GenerateResponse(BaseModel):
    generation_run_id: str
    story_id: str
    status: str
    estimated_completion_seconds: int = 25


class PatchTestCaseRequest(BaseModel):
    status: Optional[str] = None  # 'approved' | 'rejected'
    title: Optional[str] = None
    test_steps: Optional[List[dict]] = None


class CoverageEntry(BaseModel):
    ac_reference: str
    positive_count: int
    negative_count: int
    edge_count: int
    total: int


class CoverageReportResponse(BaseModel):
    story_id: str
    coverage: List[CoverageEntry]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/stories/{story_id}/generate-test-cases",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenerateResponse,
)
def generate_test_cases(story_id: str, body: GenerateRequest) -> GenerateResponse:
    """Enqueue a test-case generation run for *story_id*.

    In production this creates a Celery task; here we record a pending run.
    """
    existing = [
        r for r in _runs.values()
        if r["story_id"] == story_id and r["status"] == "running"
    ]
    if existing and not body.regenerate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A generation run is already in progress for this story. "
                   "Set regenerate=true to force a new run.",
        )

    run_id = str(uuid.uuid4())
    _runs[run_id] = {
        "generation_run_id": run_id,
        "story_id": story_id,
        "status": "running",
        "options": body.options.model_dump(),
    }
    return GenerateResponse(
        generation_run_id=run_id,
        story_id=story_id,
        status="running",
    )


@router.get("/stories/{story_id}/test-cases")
def list_test_cases(story_id: str) -> dict:
    """Return all non-rejected test cases for *story_id*."""
    cases = [
        tc for tc in _test_cases.values()
        if tc["story_id"] == story_id
    ]
    return {"story_id": story_id, "total": len(cases), "test_cases": cases}


@router.patch("/test-cases/{tc_id}")
def patch_test_case(tc_id: str, body: PatchTestCaseRequest) -> dict:
    """Approve, reject, or edit a generated test case."""
    tc = _test_cases.get(tc_id)
    if tc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test case not found.")

    allowed_statuses = {"approved", "rejected", "draft"}
    if body.status is not None:
        if body.status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"status must be one of {allowed_statuses}",
            )
        tc["status"] = body.status
    if body.title is not None:
        tc["title"] = body.title
    if body.test_steps is not None:
        tc["test_steps"] = body.test_steps

    return tc


@router.get("/stories/{story_id}/coverage-report", response_model=CoverageReportResponse)
def coverage_report(story_id: str) -> CoverageReportResponse:
    """Aggregate AC coverage across approved/draft test cases."""
    cases = [
        tc for tc in _test_cases.values()
        if tc["story_id"] == story_id and tc.get("status") != "rejected"
    ]
    by_ac: Dict[str, Dict[str, int]] = {}
    for tc in cases:
        ref = tc.get("ac_reference", "unknown")
        bucket = by_ac.setdefault(ref, {"positive": 0, "negative": 0, "edge": 0})
        t = tc.get("test_type", "")
        if t == "positive":
            bucket["positive"] += 1
        elif t == "negative":
            bucket["negative"] += 1
        elif t in ("edge", "boundary"):
            bucket["edge"] += 1

    coverage = [
        CoverageEntry(
            ac_reference=ref,
            positive_count=v["positive"],
            negative_count=v["negative"],
            edge_count=v["edge"],
            total=v["positive"] + v["negative"] + v["edge"],
        )
        for ref, v in by_ac.items()
    ]
    return CoverageReportResponse(story_id=story_id, coverage=coverage)
