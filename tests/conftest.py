"""Shared pytest fixtures."""
import pytest


@pytest.fixture
def sample_embedding() -> list[float]:
    """Return a deterministic dummy embedding vector."""
    return [0.1] * 1536
