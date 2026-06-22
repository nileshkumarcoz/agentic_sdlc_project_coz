from dataclasses import dataclass
from typing import List

from src.agentic_sdlc.clients.llm_client import BaseLLMClient, LLMMessage


@dataclass
class ReviewResult:
    feedback: str


SYSTEM_PROMPT = (
    "You are an expert code reviewer. "
    "Analyse the provided code snippet and return concise, actionable feedback."
)


class CodeReviewAgent:
    def __init__(self, llm_client: BaseLLMClient) -> None:
        self._llm = llm_client

    def review(self, code_snippet: str) -> ReviewResult:
        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=SYSTEM_PROMPT),
            LLMMessage(role="user", content=f"Review this code:\n```\n{code_snippet}\n```"),
        ]
        response = self._llm.complete(messages)
        return ReviewResult(feedback=response.content)
