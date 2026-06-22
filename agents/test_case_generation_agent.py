"""TestCaseGenerationAgent — orchestrates story analysis and test case generation.

Phase 1/2 implementation: agent skeleton + four tool stubs with typed interfaces.
LLM calls are injected via an llm_fn callable so the agent is fully unit-testable.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared data models
# ---------------------------------------------------------------------------

class ACItem(BaseModel):
    id: str
    given: str
    when: str
    then: str


class StoryAnalysis(BaseModel):
    actors: List[str] = Field(default_factory=list)
    functional_actions: List[str] = Field(default_factory=list)
    ac_items: List[ACItem] = Field(default_factory=list)
    business_rules: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class TestStep(BaseModel):
    step: int
    action: str
    expected_result: str


class TestData(BaseModel):
    label: str
    value: str
    reason: str
    validity: str  # 'valid' | 'invalid'


class TestCase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ac_reference: str
    title: str
    preconditions: Optional[str] = None
    test_steps: List[TestStep] = Field(default_factory=list)
    expected_result: str
    test_type: str  # 'positive' | 'negative' | 'edge' | 'boundary'
    test_data: List[TestData] = Field(default_factory=list)
    status: str = "draft"


@dataclass
class GenerationOptions:
    include_edge_cases: bool = True
    include_test_data: bool = True
    max_cases_per_ac: int = 10


@dataclass
class GenerationResult:
    generation_run_id: str
    story_id: str
    status: str
    test_cases: List[TestCase] = field(default_factory=list)
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

LLMFn = Callable[[str, str], Any]  # (system_prompt, user_prompt) -> parsed JSON


class StoryAnalyserTool:
    """Extracts actors, ACs, and constraints from a raw story dict."""

    SYSTEM = (
        "You are a senior QA analyst. Extract structured information from the "
        "following user story. Return ONLY valid JSON matching: "
        '{actors:[], functional_actions:[], ac_items:[{id,given,when,then}], '
        "business_rules:[], constraints:[]}."
    )

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def run(self, story: dict) -> StoryAnalysis:
        user_prompt = (
            f"Title: {story.get('title', '')}\n"
            f"Description: {story.get('description', '')}\n"
            f"Acceptance Criteria: {story.get('acceptance_criteria', '')}"
        )
        raw = self._llm(self.SYSTEM, user_prompt)
        return StoryAnalysis.model_validate(raw)


class TestCaseBuilderTool:
    """Generates positive/negative test cases for each AC item."""

    SYSTEM = (
        "You are a QA expert. Given the extracted requirements below, generate "
        "comprehensive test cases. For EACH acceptance criterion produce at least "
        "2 positive and 2 negative test cases. Return a JSON array: "
        "[{ac_reference, title, preconditions, "
        "test_steps:[{step,action,expected_result}], expected_result, test_type}]"
    )

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def run(self, analysis: StoryAnalysis) -> List[TestCase]:
        user_prompt = f"Extracted Requirements: {analysis.model_dump_json()}"
        raw = self._llm(self.SYSTEM, user_prompt)
        return [TestCase.model_validate(tc) for tc in raw]


class EdgeCaseIdentifierTool:
    """Applies boundary-value and equivalence-partition analysis."""

    SYSTEM = (
        "You are a boundary-value analysis expert. Identify: boundary value cases, "
        "equivalence partitions, state-transition edges, and error/exception paths. "
        "Return a JSON array with test_type set to 'edge' or 'boundary'."
    )

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def run(self, analysis: StoryAnalysis, existing_cases: List[TestCase]) -> List[TestCase]:
        user_prompt = (
            f"Business Rules: {json.dumps(analysis.business_rules)}\n"
            f"Constraints: {json.dumps(analysis.constraints)}\n"
            f"Existing cases count: {len(existing_cases)}"
        )
        raw = self._llm(self.SYSTEM, user_prompt)
        return [TestCase.model_validate(tc) for tc in raw]


class TestDataRecommenderTool:
    """Enriches each test case with valid/invalid test data recommendations."""

    SYSTEM = (
        "For each test case provided, recommend specific test data (valid and invalid "
        "examples with a reason). Return the same array enriched with "
        "test_data:[{label, value, reason, validity:'valid'|'invalid'}]."
    )

    def __init__(self, llm_fn: LLMFn) -> None:
        self._llm = llm_fn

    def run(self, test_cases: List[TestCase], analysis: StoryAnalysis) -> List[TestCase]:
        user_prompt = (
            f"Test Cases: {json.dumps([tc.model_dump() for tc in test_cases])}\n"
            f"Constraints: {json.dumps(analysis.constraints)}"
        )
        raw = self._llm(self.SYSTEM, user_prompt)
        return [TestCase.model_validate(tc) for tc in raw]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class TestCaseGenerationAgent:
    """Orchestrates the four tools to generate test cases from a user story.

    Args:
        llm_fn: Callable(system_prompt, user_prompt) -> parsed JSON object.
                Swap for a real LLM adapter in production.
        story_repo: Object with a ``get_approved(story_id) -> dict`` method.
                    If None the caller must pass the story dict directly to ``run``.
    """

    def __init__(self, llm_fn: LLMFn, story_repo: Any = None) -> None:
        self._story_repo = story_repo
        self.story_analyser = StoryAnalyserTool(llm_fn)
        self.test_case_builder = TestCaseBuilderTool(llm_fn)
        self.edge_case_identifier = EdgeCaseIdentifierTool(llm_fn)
        self.test_data_recommender = TestDataRecommenderTool(llm_fn)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(
        self,
        story_id: str,
        options: Optional[GenerationOptions] = None,
        story: Optional[dict] = None,
    ) -> GenerationResult:
        """Run the full generation pipeline.

        ``story`` may be supplied directly (useful in tests / on-demand API calls);
        otherwise it is fetched via ``story_repo``.
        """
        options = options or GenerationOptions()
        run_id = str(uuid.uuid4())

        try:
            if story is None:
                if self._story_repo is None:
                    raise ValueError("Either story or story_repo must be provided.")
                story = self._story_repo.get_approved(story_id)

            analysis = self.story_analyser.run(story)
            test_cases = self.test_case_builder.run(analysis)

            if options.include_edge_cases:
                edge_cases = self.edge_case_identifier.run(analysis, test_cases)
                test_cases = test_cases + edge_cases

            if options.include_test_data:
                test_cases = self.test_data_recommender.run(test_cases, analysis)

            # Apply per-AC cap
            test_cases = self._apply_cap(test_cases, options.max_cases_per_ac)

            return GenerationResult(
                generation_run_id=run_id,
                story_id=story_id,
                status="completed",
                test_cases=test_cases,
            )
        except Exception as exc:  # noqa: BLE001
            return GenerationResult(
                generation_run_id=run_id,
                story_id=story_id,
                status="failed",
                error_message=str(exc),
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_cap(test_cases: List[TestCase], max_per_ac: int) -> List[TestCase]:
        """Trim test cases so no AC reference exceeds *max_per_ac* cases."""
        counts: dict[str, int] = {}
        result: List[TestCase] = []
        for tc in test_cases:
            ref = tc.ac_reference
            if counts.get(ref, 0) < max_per_ac:
                result.append(tc)
                counts[ref] = counts.get(ref, 0) + 1
        return result

    @staticmethod
    def content_hash(story: dict) -> str:
        """SHA-256 of story content — used as LLM cache key."""
        payload = json.dumps(story, sort_keys=True).encode()
        return hashlib.sha256(payload).hexdigest()
