"""LangGraph StateGraph wiring for the parking chatbot."""
from langgraph.graph import END, START, StateGraph

from chatbot.workflow.nodes import (
    approval_request_node,
    dynamic_data_node,
    guard_rails_node,
    out_of_scope_node,
    pending_check_node,
    reservation_collector_node,
    reservation_validator_node,
    respond,
    retrieve_and_generate,
    route_intent,
)
from chatbot.workflow.state import ConversationState

_DYNAMIC_INTENTS = {"pricing", "hours", "availability"}


def _route_after_intent(state: ConversationState) -> str:
    intent = state.intent or "out_of_scope"
    if intent == "info_query":
        return "retrieve_and_generate"
    if intent in _DYNAMIC_INTENTS:
        return "dynamic_data_node"
    if intent == "reservation":
        return "reservation_collector_node"
    return "out_of_scope_node"


def _route_after_reservation_validator(state: ConversationState) -> str:
    if state.reservation and state.reservation.status == "submitted":
        return "approval_request_node"
    return "respond"


def _route_after_pending_check(state: ConversationState) -> str:
    # If response_draft was set by pending_check_node, route to guard_rails
    if state.response_draft is not None:
        return "guard_rails_node"
    return "route_intent"


def build_graph() -> StateGraph:
    graph = StateGraph(ConversationState)

    graph.add_node("pending_check_node", pending_check_node)
    graph.add_node("route_intent", route_intent)
    graph.add_node("retrieve_and_generate", retrieve_and_generate)
    graph.add_node("dynamic_data_node", dynamic_data_node)
    graph.add_node("out_of_scope_node", out_of_scope_node)
    graph.add_node("reservation_collector_node", reservation_collector_node)
    graph.add_node("reservation_validator_node", reservation_validator_node)
    graph.add_node("approval_request_node", approval_request_node)
    graph.add_node("guard_rails_node", guard_rails_node)
    graph.add_node("respond", respond)

    # pending_check_node is the first node — checks for waiting admin decisions
    graph.add_edge(START, "pending_check_node")
    graph.add_conditional_edges(
        "pending_check_node",
        _route_after_pending_check,
        {
            "guard_rails_node": "guard_rails_node",
            "route_intent": "route_intent",
        },
    )

    graph.add_conditional_edges(
        "route_intent",
        _route_after_intent,
        {
            "retrieve_and_generate": "retrieve_and_generate",
            "dynamic_data_node": "dynamic_data_node",
            "reservation_collector_node": "reservation_collector_node",
            "out_of_scope_node": "out_of_scope_node",
        },
    )

    # Static Q&A and dynamic data both go through guard rails
    graph.add_edge("retrieve_and_generate", "guard_rails_node")
    graph.add_edge("dynamic_data_node", "guard_rails_node")
    graph.add_edge("out_of_scope_node", "guard_rails_node")

    # Reservation path
    graph.add_edge("reservation_collector_node", "reservation_validator_node")
    graph.add_conditional_edges(
        "reservation_validator_node",
        _route_after_reservation_validator,
        {
            "approval_request_node": "approval_request_node",
            "respond": "respond",
        },
    )
    graph.add_edge("approval_request_node", "guard_rails_node")

    graph.add_edge("guard_rails_node", "respond")
    graph.add_edge("respond", END)

    return graph


# Module-level compiled graph
compiled_graph = build_graph().compile()
