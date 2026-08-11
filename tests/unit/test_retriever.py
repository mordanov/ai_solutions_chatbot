"""Unit tests for ParkingRetriever (vector store mocked)."""
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document

from chatbot.rag.retriever import ParkingRetriever


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.similarity_search.return_value = [
        Document(
            page_content="Top result",
            metadata={"id": "c1", "score": 0.95},
        ),
        Document(
            page_content="Second result",
            metadata={"id": "c2", "score": 0.80},
        ),
    ]
    return store


@pytest.fixture
def empty_store():
    store = MagicMock()
    store.similarity_search.return_value = []
    return store


def test_retriever_returns_top_k_documents(mock_store):
    """Retriever returns documents sorted by similarity."""
    retriever = ParkingRetriever(vector_store=mock_store, top_k=2)
    results = retriever.retrieve("Where is the parking?", embedding=[0.1] * 1536)

    assert len(results) == 2
    assert results[0].page_content == "Top result"
    mock_store.similarity_search.assert_called_once()


def test_retriever_handles_empty_result(empty_store):
    """Retriever returns an empty list without raising when nothing matches."""
    retriever = ParkingRetriever(vector_store=empty_store, top_k=5)
    results = retriever.retrieve("Completely unrelated query", embedding=[0.0] * 1536)

    assert results == []
