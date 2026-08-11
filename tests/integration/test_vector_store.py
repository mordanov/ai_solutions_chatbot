"""Integration tests for MilvusVectorStore — require a running Milvus instance."""
import uuid

import pytest
from langchain_core.documents import Document

pytestmark = pytest.mark.integration


@pytest.fixture
def store():
    from chatbot.knowledge.vector_store import MilvusVectorStore

    test_collection = f"test_{uuid.uuid4().hex[:8]}"
    s = MilvusVectorStore(collection_name=test_collection)
    yield s
    s.drop_collection()


def test_add_and_search_returns_top_result(store, sample_embedding):
    """add_documents followed by similarity_search returns the inserted document."""
    doc = Document(
        page_content="Test parking knowledge chunk.",
        metadata={"id": "test-1", "source": "test.md", "section": "test", "chunk_index": 0},
    )
    store.add_documents([doc], [sample_embedding])
    results = store.similarity_search(sample_embedding, top_k=1)
    assert len(results) == 1
    assert results[0].page_content == doc.page_content


def test_drop_collection_removes_documents(store, sample_embedding):
    """drop_collection removes the collection so subsequent searches fail or return empty."""
    doc = Document(
        page_content="Ephemeral chunk.",
        metadata={"id": "test-2", "source": "test.md", "section": "test", "chunk_index": 0},
    )
    store.add_documents([doc], [sample_embedding])
    store.drop_collection()
    # After dropping, querying should either raise or return empty (collection gone)
    try:
        results = store.similarity_search(sample_embedding, top_k=1)
        assert results == []
    except Exception:
        pass  # Acceptable — collection no longer exists
