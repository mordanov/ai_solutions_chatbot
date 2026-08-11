"""Unit tests for workflow nodes (LLM and external services mocked)."""
from unittest.mock import MagicMock, patch

from langchain_core.messages import HumanMessage

from chatbot.workflow.state import ConversationState, ReservationData


def _base_state(**kwargs) -> ConversationState:
    return ConversationState(
        session_id="test-session",
        messages=[HumanMessage(content="Hello")],
        **kwargs,
    )


# ------------------------------------------------------------------
# route_intent
# ------------------------------------------------------------------

def test_route_intent_classifies_info_query():
    with patch("chatbot.workflow.nodes._get_llm") as mock_llm_fn:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="info_query")
        mock_llm_fn.return_value = mock_llm

        from chatbot.workflow.nodes import route_intent

        state = _base_state()
        result = route_intent(state)
        assert result.intent == "info_query"


def test_route_intent_unknown_falls_back_to_info_query():
    with patch("chatbot.workflow.nodes._get_llm") as mock_llm_fn:
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="gibberish_intent_xyz")
        mock_llm_fn.return_value = mock_llm

        from chatbot.workflow.nodes import route_intent

        state = _base_state()
        result = route_intent(state)
        assert result.intent == "info_query"


# ------------------------------------------------------------------
# reservation_validator_node
# ------------------------------------------------------------------

def test_reservation_validator_submits_complete_draft():
    reservation = ReservationData(
        first_name="Alice",
        surname="Smith",
        license_plate="AB1234",
        start_datetime="2026-09-01 10:00",
        end_datetime="2026-09-01 14:00",
    )
    state = _base_state(reservation=reservation)

    from chatbot.workflow.nodes import reservation_validator_node

    result = reservation_validator_node(state)
    assert result.reservation is not None
    assert result.reservation.status == "submitted"


def test_reservation_validator_prompts_for_missing_plate():
    reservation = ReservationData(
        first_name="Bob",
        surname="Jones",
        # license_plate missing
        start_datetime="2026-09-01 10:00",
        end_datetime="2026-09-01 14:00",
    )
    state = _base_state(reservation=reservation)

    from chatbot.workflow.nodes import reservation_validator_node

    result = reservation_validator_node(state)
    assert result.reservation is not None
    assert result.reservation.status == "draft"
    assert "licence plate" in (result.response_draft or "").lower()
