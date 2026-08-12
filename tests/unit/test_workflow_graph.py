"""Unit tests for the LangGraph routing functions in workflow/graph.py."""
from chatbot.workflow.graph import (
    _route_after_intent,
    _route_after_pending_check,
    _route_after_reservation_validator,
)
from chatbot.workflow.state import ConversationState, ReservationData


def _state(**kwargs) -> ConversationState:
    return ConversationState(session_id="test", **kwargs)


# ------------------------------------------------------------------
# _route_after_intent
# ------------------------------------------------------------------

def test_route_after_intent_info_query():
    assert _route_after_intent(_state(intent="info_query")) == "retrieve_and_generate"


def test_route_after_intent_reservation():
    assert _route_after_intent(_state(intent="reservation")) == "reservation_collector_node"


def test_route_after_intent_pricing():
    assert _route_after_intent(_state(intent="pricing")) == "dynamic_data_node"


def test_route_after_intent_unknown_falls_back_to_out_of_scope():
    assert _route_after_intent(_state(intent="something_unknown")) == "out_of_scope_node"


# ------------------------------------------------------------------
# _route_after_reservation_validator
# ------------------------------------------------------------------

def test_route_after_reservation_validator_submitted():
    state = _state(reservation=ReservationData(status="submitted"))
    assert _route_after_reservation_validator(state) == "approval_request_node"


def test_route_after_reservation_validator_draft():
    state = _state(reservation=ReservationData(status="draft"))
    assert _route_after_reservation_validator(state) == "respond"


# ------------------------------------------------------------------
# _route_after_pending_check
# ------------------------------------------------------------------

def test_route_after_pending_check_with_draft():
    state = _state(response_draft="Admin has decided.")
    assert _route_after_pending_check(state) == "guard_rails_node"


def test_route_after_pending_check_no_draft():
    state = _state(response_draft=None)
    assert _route_after_pending_check(state) == "route_intent"
