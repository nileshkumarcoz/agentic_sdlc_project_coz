"""Unit tests for TestCaseGenerationAgent and its tools."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agents.test_case_generation_agent import (
    ACItem,
    EdgeCaseIdentifierTool,
    GenerationOptions,
    StoryAnalysis,
    StoryAnalyserTool,
    TestCase,
    TestCaseBuilderTool,
    TestCaseGenerationAgent,
    TestDataRecommenderTool,
    TestStep,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_STORY = {
    "id": "109095",
    "title": "Generate test cases from user stories",
    "description": "As a QA engineer I want the system to auto-generate test cases.",
    "acceptance_criteria": "AC1: Given an approved story, when I trigger generation, then test cases are created.",
}

SAMPLE_ANALYSIS_DICT = {
    "actors": ["QA Engineer"],
    "functional_actions": ["generate test cases"],
    "ac_items": [{"id": "AC1", "given": "approved story", "when": "trigger generation", "then": "cases created"}],
    "business_rules": ["Max 10 cases per AC"],
    "constraints": ["Story must be approved"],
}

SAMPLE_TC_DICT = {
    "ac_reference": "AC1",
    "title": "Verify test case generation for approved story",
    "preconditions": "Story 109095 is in approved state",
    "test_steps": [{"step": 1, "action": "Submit story ID", "expected_result": "Cases returned"}],
    "expected_result": "Test cases are created with status=draft",
    "test_type": "positive",
    "test_data": [],
}

SAMPLE_TC_WITH_DATA_DICT = {
    **SAMPLE_TC_DICT,
    "test_data": [{"label": "story_id", "value": "109095", "reason": "Valid approved story", "validity": "valid"}],
}


def make_llm_fn(return_value: Any):
    """Return a mock LLM callable that always returns *return_value*."""
    return MagicMock(return_value=return_value)


# ---------------------------------------------------------------------------
# StoryAnalyserTool
# ---------------------------------------------------------------------------

class TestStoryAnalyserTool:
    def test_returns_story_analysis(self):
        llm = make_llm_fn(SAMPLE_ANALYSIS_DICT)
        tool = StoryAnalyserTool(llm)
        result = tool.run(SAMPLE_STORY)
        assert isinstance(result, StoryAnalysis)
        assert result.actors == ["QA Engineer"]
        assert len(result.ac_items) == 1
        assert result.ac_items[0].id == "AC1"

    def test_llm_called_with_story_content(self):
        llm = make_llm_fn(SAMPLE_ANALYSIS_DICT)
        tool = StoryAnalyserTool(llm)
        tool.run(SAMPLE_STORY)
        call_args = llm.call_args
        assert "Generate test cases from user stories" in call_args[0][1]


# ---------------------------------------------------------------------------
# TestCaseBuilderTool
# ---------------------------------------------------------------------------

class TestTestCaseBuilderTool:
    def test_returns_list_of_test_cases(self):
        tc_list = [SAMPLE_TC_DICT, {**SAMPLE_TC_DICT, "test_type": "negative"}]
        llm = make_llm_fn(tc_list)
        tool = TestCaseBuilderTool(llm)
        analysis = StoryAnalysis.model_validate(SAMPLE_ANALYSIS_DICT)
        result = tool.run(analysis)
        assert len(result) == 2
        assert all(isinstance(tc, TestCase) for tc in result)

    def test_test_types_preserved(self):
        tc_list = [SAMPLE_TC_DICT, {**SAMPLE_TC_DICT, "test_type": "negative"}]
        llm = make_llm_fn(tc_list)
        tool = TestCaseBuilderTool(llm)
        analysis = StoryAnalysis.model_validate(SAMPLE_ANALYSIS_DICT)
        result = tool.run(analysis)
        types = {tc.test_type for tc in result}
        assert "positive" in types
        assert "negative" in types


# ---------------------------------------------------------------------------
# EdgeCaseIdentifierTool
# ---------------------------------------------------------------------------

class TestEdgeCaseIdentifierTool:
    def test_returns_edge_cases(self):
        edge_dict = {**SAMPLE_TC_DICT, "test_type": "edge"}
        llm = make_llm_fn([edge_dict])
        tool = EdgeCaseIdentifierTool(llm)
        analysis = StoryAnalysis.model_validate(SAMPLE_ANALYSIS_DICT)
        result = tool.run(analysis, [])
        assert len(result) == 1
        assert result[0].test_type == "edge"


# ---------------------------------------------------------------------------
# TestDataRecommenderTool
# ---------------------------------------------------------------------------

class TestTestDataRecommenderTool:
    def test_enriches_test_cases_with_data(self):
        llm = make_llm_fn([SAMPLE_TC_WITH_DATA_DICT])
        tool = TestDataRecommenderTool(llm)
        analysis = StoryAnalysis.model_validate(SAMPLE_ANALYSIS_DICT)
        base_tc = TestCase.model_validate(SAMPLE_TC_DICT)
        result = tool.run([base_tc], analysis)
        assert len(result[0].test_data) == 1
        assert result[0].test_data[0].validity == "valid"


# ---------------------------------------------------------------------------
# TestCaseGenerationAgent
# ---------------------------------------------------------------------------

class TestTestCaseGenerationAgent:
    def _make_agent(self, tc_list=None, edge_list=None, enriched_list=None):
        """Build an agent whose tools return deterministic canned data."""
        analysis = StoryAnalysis.model_validate(SAMPLE_ANALYSIS_DICT)
        tc_list = tc_list or [TestCase.model_validate(SAMPLE_TC_DICT)]
        edge_list = edge_list or [TestCase.model_validate({**SAMPLE_TC_DICT, "test_type": "edge"})]
        enriched_list = enriched_list or [
            TestCase.model_validate(SAMPLE_TC_WITH_DATA_DICT),
            TestCase.model_validate({**SAMPLE_TC_WITH_DATA_DICT, "test_type": "edge"}),
        ]

        agent = TestCaseGenerationAgent(llm_fn=MagicMock())
        agent.story_analyser.run = MagicMock(return_value=analysis)
        agent.test_case_builder.run = MagicMock(return_value=tc_list)
        agent.edge_case_identifier.run = MagicMock(return_value=edge_list)
        agent.test_data_recommender.run = MagicMock(return_value=enriched_list)
        return agent

    def test_completed_status_on_success(self):
        agent = self._make_agent()
        result = agent.run("109095", story=SAMPLE_STORY)
        assert result.status == "completed"
        assert result.story_id == "109095"

    def test_test_cases_populated(self):
        agent = self._make_agent()
        result = agent.run("109095", story=SAMPLE_STORY)
        assert len(result.test_cases) > 0
        assert all(isinstance(tc, TestCase) for tc in result.test_cases)

    def test_edge_cases_excluded_when_option_false(self):
        agent = self._make_agent()
        opts = GenerationOptions(include_edge_cases=False, include_test_data=False)
        result = agent.run("109095", options=opts, story=SAMPLE_STORY)
        agent.edge_case_identifier.run.assert_not_called()
        assert result.status == "completed"

    def test_test_data_excluded_when_option_false(self):
        agent = self._make_agent()
        opts = GenerationOptions(include_test_data=False)
        result = agent.run("109095", options=opts, story=SAMPLE_STORY)
        agent.test_data_recommender.run.assert_not_called()

    def test_cap_applied_per_ac(self):
        # Build 5 cases all under AC1; cap at 2
        many_cases = [TestCase.model_validate(SAMPLE_TC_DICT) for _ in range(5)]
        agent = self._make_agent(tc_list=many_cases, edge_list=[], enriched_list=many_cases)
        opts = GenerationOptions(include_edge_cases=False, include_test_data=True, max_cases_per_ac=2)
        result = agent.run("109095", options=opts, story=SAMPLE_STORY)
        assert len(result.test_cases) <= 2

    def test_failed_status_on_error(self):
        agent = TestCaseGenerationAgent(llm_fn=MagicMock())
        agent.story_analyser.run = MagicMock(side_effect=RuntimeError("LLM timeout"))
        result = agent.run("109095", story=SAMPLE_STORY)
        assert result.status == "failed"
        assert "LLM timeout" in result.error_message

    def test_requires_story_or_repo(self):
        agent = TestCaseGenerationAgent(llm_fn=MagicMock(), story_repo=None)
        result = agent.run("109095")  # no story, no repo
        assert result.status == "failed"

    def test_content_hash_deterministic(self):
        h1 = TestCaseGenerationAgent.content_hash(SAMPLE_STORY)
        h2 = TestCaseGenerationAgent.content_hash(SAMPLE_STORY)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_generation_run_id_is_uuid(self):
        agent = self._make_agent()
        result = agent.run("109095", story=SAMPLE_STORY)
        # Should not raise
        import uuid as _uuid
        _uuid.UUID(result.generation_run_id)
