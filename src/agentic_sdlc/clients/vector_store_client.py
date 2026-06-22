from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


@dataclass
class Document:
    id: str
    content: str
    metadata: dict = field(default_factory=dict)


class BaseVectorStoreClient(ABC):
    @abstractmethod
    def upsert(self, documents: List[Document]) -> None: ...

    @abstractmethod
    def query(self, query_text: str, top_k: int = 5) -> List[Document]: ...
