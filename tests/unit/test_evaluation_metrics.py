"""Unit tests for Recall@K and Precision@K metrics."""
import pytest

from chatbot.evaluation.metrics import precision_at_k, recall_at_k


def test_recall_at_k_perfect_retrieval():
    assert recall_at_k(["a", "b", "c"], ["a", "b", "c"], k=5) == 1.0


def test_recall_at_k_no_relevant_retrieved():
    assert recall_at_k(["x", "y"], ["a", "b"], k=5) == 0.0


def test_recall_at_k_partial():
    result = recall_at_k(["a", "x", "y"], ["a", "b"], k=5)
    assert result == pytest.approx(0.5)


def test_precision_at_k_all_relevant():
    assert precision_at_k(["a", "b"], ["a", "b", "c"], k=2) == 1.0


def test_precision_at_k_none_relevant():
    assert precision_at_k(["x", "y"], ["a", "b"], k=2) == 0.0


def test_precision_at_k_zero_k():
    assert precision_at_k(["a"], ["a"], k=0) == 0.0
