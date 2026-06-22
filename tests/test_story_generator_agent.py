"""Unit tests for StoryGeneratorAgent and the FastAPI route."""
from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.agents.story_generator_agent import (
    DocumentParserTool,
    StoryGeneratorAgent,
    UserStory,
)
from app.api.routes.story_generator import router

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_STORIES = [
    {
        "title": "User login",
        "description": "As a user I want to log in so that I can access my data",
        "acceptance_criteria": ["Given valid credentials, login succeeds"],
        "priority": "High",
        "points": 5,
    }
]


def _make_llm_mock(payload=None):
    payload = payload or SAMPLE_STORIES
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = json.dumps(payload)
    mock_llm.return_value = mock_response
    return mock_llm


# ---------------------------------------------------------------------------
# DocumentParserTool tests
# ---------------------------------------------------------------------------


def test_parser_txt_bytes():
    parser = DocumentParserTool()
    result = parser.parse(b"Hello requirements", "reqs.txt")
    assert result == "Hello requirements"


def test_parser_md_string():
    parser = DocumentParserTool()
    result = parser.parse("# Requirements\n- FR-1", "spec.md")
    assert "FR-1" in result


def test_parser_unsupported_raises():
    parser = DocumentParserTool()
    with pytest.raises(ValueError, match="Unsupported"):
        parser.parse(b"%PDF", "doc.pdf")


# ---------------------------------------------------------------------------
# StoryGeneratorAgent tests
# ---------------------------------------------------------------------------


def test_agent_run_returns_user_stories():
    mock_llm = _make_llm_mock()
    agent = StoryGeneratorAgent(llm=mock_llm)
    stories = agent.run("FR-1: Users must authenticate.", "reqs.txt")
    assert len(stories) == 1
    assert isinstance(stories[0], UserStory)
    assert stories[0].title == "User login"
    assert stories[0].points == 5


def test_agent_strips_markdown_fences():
    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = f"```json\n{json.dumps(SAMPLE_STORIES)}\n```"
    mock_llm.return_value = mock_resp
    agent = StoryGeneratorAgent(llm=mock_llm)
    stories = agent.run("some requirement", "reqs.txt")
    assert len(stories) == 1


def test_agent_invalid_json_raises():
    mock_llm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.content = "not json at all"
    mock_llm.return_value = mock_resp
    agent = StoryGeneratorAgent(llm=mock_llm)
    with pytest.raises(Exception):
        agent.run("requirement text", "reqs.txt")


# ---------------------------------------------------------------------------
# FastAPI route tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_generate_endpoint_success(client):
    mock_llm = _make_llm_mock()
    with patch(
        "app.api.routes.story_generator._get_agent",
        return_value=StoryGeneratorAgent(llm=mock_llm),
    ):
        resp = client.post(
            "/api/v1/stories/generate",
            files={"file": ("reqs.txt", BytesIO(b"FR-1: login"), "text/plain")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "stories" in data
    assert data["stories"][0]["title"] == "User login"


def test_generate_endpoint_unsupported_type(client):
    with patch(
        "app.api.routes.story_generator._get_agent",
        return_value=StoryGeneratorAgent(llm=_make_llm_mock()),
    ):
        resp = client.post(
            "/api/v1/stories/generate",
            files={"file": ("spec.pdf", BytesIO(b"%PDF"), "application/pdf")},
        )
    assert resp.status_code in {415, 422}  # file type rejected
