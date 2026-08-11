"""Unit tests for the RAG pipeline (LLM and vector store mocked)."""
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document


@pytest.fixture
def mock_chunks():
    return [
        Document(
            page_content="Parking is located at 42 Market Street.",
            metadata={"id": "chunk-1", "source": "location.md", "section": "location"},
        )
    ]


def test_rag_pipeline_returns_grounded_response(mock_chunks):
    """RAG chain returns a response when context chunks are available."""
    with (
        patch("chatbot.rag.pipeline.ChatOpenAI") as mock_llm_cls,
        patch("chatbot.rag.pipeline.OpenAIEmbeddings"),
    ):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.invoke.return_value = MagicMock(content="The parking is at 42 Market Street.")

        from chatbot.rag.pipeline import build_rag_chain

        chain = build_rag_chain(mock_llm)
        result = chain({"question": "Where is the parking?", "context": mock_chunks})

        assert result is not None
        assert len(result) > 0


def test_rag_pipeline_returns_fallback_when_no_chunks():
    """RAG chain returns a safe fallback message when no context is available."""
    with (
        patch("chatbot.rag.pipeline.ChatOpenAI") as mock_llm_cls,
        patch("chatbot.rag.pipeline.OpenAIEmbeddings"),
    ):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm

        from chatbot.rag.pipeline import FALLBACK_MESSAGE, build_rag_chain

        chain = build_rag_chain(mock_llm)
        result = chain({"question": "Random question", "context": []})

        assert FALLBACK_MESSAGE in result
