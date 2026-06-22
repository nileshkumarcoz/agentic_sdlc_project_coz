from typing import Iterator, List

from src.agentic_sdlc.clients.llm_client import BaseLLMClient, LLMMessage, LLMResponse


class MockLLMClient(BaseLLMClient):
    """Configurable mock LLM client for unit tests."""

    def __init__(self, default_response: str = "mock response") -> None:
        self._default_response = default_response
        self._responses: list = []
        self._side_effect = None
        self.call_log: list = []

    def set_response(self, response: str) -> None:
        self._responses.append(response)

    def set_side_effect(self, effect) -> None:
        """Pass an Exception instance or class to simulate failures."""
        self._side_effect = effect

    def complete(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        self.call_log.append({"method": "complete", "messages": messages, "kwargs": kwargs})
        if self._side_effect is not None:
            raise self._side_effect if isinstance(self._side_effect, Exception) else self._side_effect()
        content = self._responses.pop(0) if self._responses else self._default_response
        return LLMResponse(
            content=content,
            model="mock-model",
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        )

    def stream(self, messages: List[LLMMessage], **kwargs) -> Iterator[str]:
        self.call_log.append({"method": "stream", "messages": messages})
        response = self.complete(messages, **kwargs)
        for word in response.content.split():
            yield word + " "
