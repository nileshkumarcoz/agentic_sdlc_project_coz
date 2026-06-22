from typing import List

from src.agentic_sdlc.clients.vector_store_client import BaseVectorStoreClient, Document


class MockVectorStoreClient(BaseVectorStoreClient):
    """In-memory mock vector store for unit tests."""

    def __init__(self) -> None:
        self._store: dict = {}
        self.upsert_log: list = []
        self.query_log: list = []

    def upsert(self, documents: List[Document]) -> None:
        self.upsert_log.append(documents)
        for doc in documents:
            self._store[doc.id] = doc

    def query(self, query_text: str, top_k: int = 5) -> List[Document]:
        self.query_log.append({"query": query_text, "top_k": top_k})
        return list(self._store.values())[:top_k]
