import pytest

from src.agentic_sdlc.agents.code_review_agent import CodeReviewAgent


class TestCodeReviewAgent:

    def test_review_returns_llm_response(self, mock_llm_client):
        mock_llm_client.set_response("LGTM: No issues found.")
        agent = CodeReviewAgent(llm_client=mock_llm_client)

        result = agent.review(code_snippet="def add(a, b): return a + b")

        assert result.feedback == "LGTM: No issues found."
        assert len(mock_llm_client.call_log) == 1
        call = mock_llm_client.call_log[0]
        assert any("add" in msg.content for msg in call["messages"])

    def test_review_raises_on_llm_error(self, mock_llm_client_with_error):
        agent = CodeReviewAgent(llm_client=mock_llm_client_with_error)

        with pytest.raises(ConnectionError, match="Simulated API timeout"):
            agent.review(code_snippet="def broken(): pass")

    def test_review_uses_system_prompt(self, mock_llm_client):
        mock_llm_client.set_response("Needs refactoring.")
        agent = CodeReviewAgent(llm_client=mock_llm_client)
        agent.review(code_snippet="x=1")

        messages = mock_llm_client.call_log[0]["messages"]
        assert messages[0].role == "system"
        assert "code" in messages[0].content.lower()

    def test_review_queues_multiple_responses(self, mock_llm_client):
        mock_llm_client.set_response("First review.")
        mock_llm_client.set_response("Second review.")
        agent = CodeReviewAgent(llm_client=mock_llm_client)

        assert agent.review("x = 1").feedback == "First review."
        assert agent.review("y = 2").feedback == "Second review."
        assert len(mock_llm_client.call_log) == 2

    def test_stream_yields_words(self, mock_llm_client):
        mock_llm_client.set_response("looks good to me")
        chunks = list(mock_llm_client.stream([]))
        assert "".join(chunks).strip() == "looks good to me"
