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


# ------------------------------------------------------------------
# retrieve_and_generate (T005)
# ------------------------------------------------------------------

def test_retrieve_and_generate_returns_rag_answer():
    with (
        patch("chatbot.workflow.nodes._get_llm") as mock_llm_fn,
        patch("chatbot.workflow.nodes._get_embedder") as mock_emb_fn,
        patch("chatbot.knowledge.vector_store.MilvusVectorStore") as mock_vs_cls,
        patch("chatbot.rag.retriever.ParkingRetriever") as mock_ret_cls,
        patch("chatbot.rag.pipeline.build_rag_chain") as mock_chain_fn,
    ):
        mock_emb_fn.return_value.embed_query.return_value = [0.1] * 8
        mock_vs_cls.return_value = MagicMock()
        mock_ret_cls.return_value.retrieve.return_value = []
        mock_chain_fn.return_value = MagicMock(return_value="The parking is open 24/7.")
        mock_llm_fn.return_value = MagicMock()

        from chatbot.workflow.nodes import retrieve_and_generate

        state = _base_state()
        result = retrieve_and_generate(state)
        assert result.response_draft == "The parking is open 24/7."


def test_retrieve_and_generate_uses_fallback_on_error():
    with (
        patch("chatbot.workflow.nodes._get_embedder") as mock_emb_fn,
    ):
        mock_emb_fn.return_value.embed_query.side_effect = RuntimeError("Milvus down")

        from chatbot.workflow.nodes import retrieve_and_generate

        state = _base_state()
        result = retrieve_and_generate(state)
        assert result.response_draft is not None
        assert "trouble" in (result.response_draft or "").lower()
        assert result.error is not None


# ------------------------------------------------------------------
# dynamic_data_node (T006)
# ------------------------------------------------------------------

def test_dynamic_data_node_pricing():
    rate = MagicMock()
    rate.rate_type = "hourly"
    rate.amount = 2.50
    rate.currency = "EUR"

    with (
        patch("chatbot.workflow.nodes._get_llm") as mock_llm_fn,
        patch("chatbot.data.repository.ParkingRepository") as mock_repo_cls,
    ):
        mock_repo_cls.return_value.get_active_rates.return_value = [rate]
        mock_llm_fn.return_value.invoke.return_value = MagicMock(content="Hourly rate is 2.50 EUR.")

        from chatbot.workflow.nodes import dynamic_data_node

        state = _base_state(intent="pricing")
        result = dynamic_data_node(state)
        assert result.response_draft == "Hourly rate is 2.50 EUR."


def test_dynamic_data_node_hours():
    hours = MagicMock()
    hours.day_of_week = 0
    hours.is_closed = False
    hours.open_time = "08:00"
    hours.close_time = "22:00"

    with (
        patch("chatbot.workflow.nodes._get_llm") as mock_llm_fn,
        patch("chatbot.data.repository.ParkingRepository") as mock_repo_cls,
    ):
        mock_repo_cls.return_value.get_all_hours.return_value = [hours]
        mock_llm_fn.return_value.invoke.return_value = MagicMock(content="Monday: 08:00–22:00.")

        from chatbot.workflow.nodes import dynamic_data_node

        state = _base_state(intent="hours")
        result = dynamic_data_node(state)
        assert result.response_draft == "Monday: 08:00–22:00."


# ------------------------------------------------------------------
# out_of_scope_node (T007)
# ------------------------------------------------------------------

def test_out_of_scope_node_sets_response_draft():
    from chatbot.workflow.nodes import out_of_scope_node

    state = _base_state()
    result = out_of_scope_node(state)
    assert "parking" in (result.response_draft or "").lower()


def test_out_of_scope_node_does_not_modify_reservation():
    from chatbot.workflow.nodes import out_of_scope_node

    state = _base_state(reservation=ReservationData(first_name="Alice"))
    result = out_of_scope_node(state)
    assert result.reservation is not None
    assert result.reservation.first_name == "Alice"


# ------------------------------------------------------------------
# reservation_collector_node (T008)
# ------------------------------------------------------------------

def test_reservation_collector_node_extracts_fields():
    import json

    with patch("chatbot.workflow.nodes._get_llm") as mock_llm_fn:
        payload = json.dumps({
            "first_name": "Alice",
            "surname": "Smith",
            "license_plate": "AB1234",
            "start_datetime": "2026-09-01 10:00",
            "end_datetime": "2026-09-02 10:00",
        })
        mock_llm_fn.return_value.invoke.return_value = MagicMock(content=payload)

        from chatbot.workflow.nodes import reservation_collector_node

        state = _base_state()
        result = reservation_collector_node(state)
        assert result.reservation is not None
        assert result.reservation.first_name == "Alice"
        assert result.reservation.license_plate == "AB1234"


def test_reservation_collector_node_no_human_message_returns_unchanged():
    from langchain_core.messages import AIMessage

    from chatbot.workflow.nodes import reservation_collector_node

    state = ConversationState(
        session_id="test",
        messages=[AIMessage(content="Hi there")],
    )
    result = reservation_collector_node(state)
    assert result.reservation is None
    assert result.error is None


# ------------------------------------------------------------------
# approval_request_node (T009)
# ------------------------------------------------------------------

def test_approval_request_node_creates_request():
    with patch("chatbot.approval.service.ApprovalService") as mock_svc_cls:
        mock_request = MagicMock()
        mock_request.request_id = "req-001"
        mock_svc_cls.return_value.create_request.return_value = mock_request

        from chatbot.workflow.nodes import approval_request_node

        reservation = ReservationData(
            first_name="Alice",
            surname="Smith",
            license_plate="AB1234",
            start_datetime="2026-09-01 10:00",
            end_datetime="2026-09-02 10:00",
            status="submitted",
        )
        state = _base_state(reservation=reservation)
        result = approval_request_node(state)
        assert result.approval_request_id == "req-001"
        assert result.reservation is not None
        assert result.reservation.status == "pending_approval"
        assert "administrator" in (result.response_draft or "").lower()


def test_approval_request_node_sets_error_on_service_failure():
    with patch("chatbot.approval.service.ApprovalService") as mock_svc_cls:
        mock_svc_cls.return_value.create_request.side_effect = RuntimeError("SMTP failure")

        from chatbot.workflow.nodes import approval_request_node

        reservation = ReservationData(
            first_name="Alice",
            surname="Smith",
            license_plate="AB1234",
            start_datetime="2026-09-01 10:00",
            end_datetime="2026-09-02 10:00",
            status="submitted",
        )
        state = _base_state(reservation=reservation)
        result = approval_request_node(state)
        assert result.error is not None
        assert result.response_draft is not None


# ------------------------------------------------------------------
# guard_rails_node (T010)
# ------------------------------------------------------------------

def test_guard_rails_node_bypasses_pii_scan_for_approval_messages():
    with (
        patch("chatbot.guard_rails.rules.RuleBlocklist") as mock_bl,
        patch("chatbot.guard_rails.scanner.PiiScanner") as mock_sc,
    ):
        from chatbot.workflow.nodes import guard_rails_node

        state = _base_state(
            response_draft="Alice Smith plate AB1234 approved",
            approval_request_id="req-001",
        )
        result = guard_rails_node(state)
        mock_bl.return_value.check.assert_not_called()
        mock_sc.return_value.scan.assert_not_called()
        assert result.response_final == "Alice Smith plate AB1234 approved"


def test_guard_rails_node_blocks_flagged_content():
    with (
        patch("chatbot.guard_rails.rules.RuleBlocklist") as mock_bl,
        patch("chatbot.guard_rails.scanner.PiiScanner") as mock_sc,
    ):
        mock_bl.return_value.check.return_value = True
        mock_sc.return_value.scan.return_value = False

        from chatbot.workflow.nodes import guard_rails_node

        state = _base_state(response_draft="Internal admin password is abc123")
        result = guard_rails_node(state)
        assert "privacy" in (result.response_final or "").lower()


# ------------------------------------------------------------------
# pending_check_node (T011, T013)
# ------------------------------------------------------------------

def test_pending_check_node_approved_sets_status():
    pending = MagicMock()
    pending.request_id = "req-001"
    pending.decision = "approved"
    pending.first_name = "Alice"
    pending.surname = "Smith"
    pending.license_plate = "AB1234"
    pending.start_datetime = "2026-09-01 10:00"
    pending.end_datetime = "2026-09-02 10:00"

    with (
        patch("chatbot.approval.store.pending_store") as mock_store,
    ):
        mock_store.get_pending_for_session.return_value = pending
        mock_store.is_expired.return_value = False

        from chatbot.workflow.nodes import pending_check_node

        reservation = ReservationData(status="pending_approval")
        state = _base_state(reservation=reservation)
        result = pending_check_node(state)
        assert result.reservation is not None
        assert result.reservation.status == "approved"
        assert "✅" in (result.response_draft or "")


def test_pending_check_node_expired_sets_status():
    pending = MagicMock()
    pending.request_id = "req-001"

    with patch("chatbot.approval.store.pending_store") as mock_store:
        mock_store.get_pending_for_session.return_value = pending
        mock_store.is_expired.return_value = True

        from chatbot.workflow.nodes import pending_check_node

        reservation = ReservationData(status="pending_approval")
        state = _base_state(reservation=reservation)
        result = pending_check_node(state)
        assert result.reservation is not None
        assert result.reservation.status == "expired"
        assert "timed out" in (result.response_draft or "").lower()


def test_pending_check_node_rejected_sets_status():
    pending = MagicMock()
    pending.request_id = "req-001"
    pending.decision = "rejected"
    pending.reason = "No spaces"

    with patch("chatbot.approval.store.pending_store") as mock_store:
        mock_store.get_pending_for_session.return_value = pending
        mock_store.is_expired.return_value = False

        from chatbot.workflow.nodes import pending_check_node

        reservation = ReservationData(status="pending_approval")
        state = _base_state(reservation=reservation)
        result = pending_check_node(state)
        assert result.reservation is not None
        assert result.reservation.status == "rejected"
        assert "❌" in (result.response_draft or "") or "not approved" in (result.response_draft or "").lower()


# ------------------------------------------------------------------
# respond (T015)
# ------------------------------------------------------------------

def test_respond_appends_ai_message_from_response_final():
    from langchain_core.messages import AIMessage

    from chatbot.workflow.nodes import respond

    state = _base_state(response_final="Your parking is confirmed.")
    result = respond(state)
    assert len(result.messages) == 2  # original HumanMessage + new AIMessage
    assert isinstance(result.messages[-1], AIMessage)
    assert result.messages[-1].content == "Your parking is confirmed."


def test_respond_uses_fallback_when_no_final_or_draft():
    from langchain_core.messages import AIMessage

    from chatbot.workflow.nodes import respond

    state = ConversationState(session_id="test", response_final=None, response_draft=None)
    result = respond(state)
    assert len(result.messages) == 1
    assert isinstance(result.messages[-1], AIMessage)
