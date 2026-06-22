from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator, List


@dataclass
class LLMMessage:
    role: str  # 'system' | 'user' | 'assistant'
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: dict = field(default_factory=dict)


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, messages: List[LLMMessage], **kwargs) -> LLMResponse: ...

    @abstractmethod
    def stream(self, messages: List[LLMMessage], **kwargs) -> Iterator[str]: ...
