import pytest

from tests.mocks.mock_llm_client import MockLLMClient
from tests.mocks.mock_vector_store_client import MockVectorStoreClient


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Fresh MockLLMClient per test."""
    return MockLLMClient()


@pytest.fixture
def mock_vector_store() -> MockVectorStoreClient:
    """Fresh MockVectorStoreClient per test."""
    return MockVectorStoreClient()


@pytest.fixture
def mock_llm_client_with_error() -> MockLLMClient:
    """MockLLMClient pre-configured to raise a ConnectionError."""
    client = MockLLMClient()
    client.set_side_effect(ConnectionError("Simulated API timeout"))
    return client
