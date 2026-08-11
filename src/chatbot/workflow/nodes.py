"""LangGraph node functions for the parking chatbot workflow."""
import logging

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from chatbot.config import settings
from chatbot.workflow.state import ConversationState

logger = logging.getLogger(__name__)

_INTENT_SYSTEM = (
    "Classify the user's latest message into exactly one intent. "
    "Reply with ONE word only: info_query, pricing, hours, availability, reservation, out_of_scope.\n"
    "info_query = general parking facts (location, rules, facilities)\n"
    "pricing = questions about rates or costs\n"
    "hours = questions about opening times\n"
    "availability = questions about free spaces\n"
    "reservation = user wants to book a space\n"
    "out_of_scope = unrelated to parking"
)


def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=0,
    )


def _get_embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )


# ------------------------------------------------------------------
# US1 — Static Q&A nodes
# ------------------------------------------------------------------

def route_intent(state: ConversationState) -> ConversationState:
    """Classify the user's latest message intent."""
    try:
        last_human = next(
            (m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None
        )
        if last_human is None:
            state.intent = "out_of_scope"
            return state

        llm = _get_llm()
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [("system", _INTENT_SYSTEM), ("human", "{message}")]
        )
        result = llm.invoke(prompt.format_messages(message=last_human.content))
        intent = result.content.strip().lower().split()[0]
        valid = {"info_query", "pricing", "hours", "availability", "reservation", "out_of_scope"}
        state.intent = intent if intent in valid else "info_query"
    except Exception as exc:
        logger.error("route_intent failed: %s", exc)
        state.error = str(exc)
        state.intent = "out_of_scope"
    return state


def retrieve_and_generate(state: ConversationState) -> ConversationState:
    """Retrieve relevant chunks and generate a grounded response."""
    try:
        from chatbot.knowledge.vector_store import MilvusVectorStore
        from chatbot.rag.pipeline import build_rag_chain
        from chatbot.rag.retriever import ParkingRetriever

        last_human = next(
            (m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None
        )
        if last_human is None:
            state.response_draft = "I couldn't find your question."
            return state

        embedder = _get_embedder()
        query_embedding = embedder.embed_query(last_human.content)

        vector_store = MilvusVectorStore()
        retriever = ParkingRetriever(vector_store, top_k=settings.retrieval_top_k)
        chunks = retriever.retrieve(last_human.content, query_embedding)
        state.retrieved_chunks = chunks

        llm = _get_llm()
        chain = build_rag_chain(llm)
        state.response_draft = chain.invoke(
            {"question": last_human.content, "context": chunks}
        )
    except Exception as exc:
        logger.error("retrieve_and_generate failed: %s", exc)
        state.error = str(exc)
        state.response_draft = (
            "I'm having trouble retrieving information right now. Please try again."
        )
    return state


def dynamic_data_node(state: ConversationState) -> ConversationState:
    """Answer pricing, hours, or availability questions from the relational DB."""
    try:
        from chatbot.data.repository import ParkingRepository

        repo = ParkingRepository(settings.database_url)
        intent = state.intent or "pricing"

        if intent == "pricing":
            rates = repo.get_active_rates()
            context = "Current parking rates:\n" + "\n".join(
                f"- {r.rate_type}: {r.amount} {r.currency}" for r in rates
            )
        elif intent == "hours":
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            all_hours = repo.get_all_hours()
            context = "Parking hours:\n" + "\n".join(
                f"- {day_names[h.day_of_week]}: {'Closed' if h.is_closed else f'{h.open_time}–{h.close_time}'}"
                for h in all_hours
            )
        else:  # availability
            avail = repo.get_availability()
            if avail:
                context = (
                    f"Available spaces: {avail.available_spaces} of {avail.total_spaces} total."
                )
            else:
                context = "Availability data is not currently available."

        last_human = next(
            (m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None
        )
        question = last_human.content if last_human else ""
        llm = _get_llm()
        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Answer using ONLY the data below. Be concise."),
                ("human", "Data:\n{context}\n\nQuestion: {question}"),
            ]
        )
        result = llm.invoke(prompt.format_messages(context=context, question=question))
        state.response_draft = result.content
    except Exception as exc:
        logger.error("dynamic_data_node failed: %s", exc)
        state.error = str(exc)
        state.response_draft = "I'm unable to retrieve that information right now."
    return state


def guard_rails_node(state: ConversationState) -> ConversationState:
    """Filter the response draft for PII and rule violations."""
    try:
        from chatbot.guard_rails.rules import RuleBlocklist
        from chatbot.guard_rails.scanner import PiiScanner

        draft = state.response_draft or ""
        blocklist = RuleBlocklist()
        scanner = PiiScanner()

        if blocklist.check(draft) or scanner.scan(draft):
            state.response_final = (
                "I'm unable to provide that information for privacy and security reasons."
            )
        else:
            state.response_final = draft
    except Exception as exc:
        logger.error("guard_rails_node failed: %s", exc)
        state.error = str(exc)
        state.response_final = state.response_draft or "An error occurred."
    return state


def respond(state: ConversationState) -> ConversationState:
    """Append the final response to the message history."""
    final = state.response_final or state.response_draft or "I couldn't generate a response."
    state.messages = list(state.messages) + [AIMessage(content=final)]
    return state


def out_of_scope_node(state: ConversationState) -> ConversationState:
    """Handle out-of-scope queries with a polite refusal."""
    state.response_draft = (
        "I can only help with questions about the parking facility. "
        "For other queries, please contact the appropriate service."
    )
    return state


# ------------------------------------------------------------------
# US3 — Reservation collector nodes (stubs expanded in Phase 6)
# ------------------------------------------------------------------

def reservation_collector_node(state: ConversationState) -> ConversationState:
    """Extract reservation fields from the latest user message."""
    try:
        from chatbot.workflow.state import ReservationData as StateReservation

        last_human = next(
            (m for m in reversed(state.messages) if isinstance(m, HumanMessage)), None
        )
        if last_human is None:
            return state

        if state.reservation is None:
            state.reservation = StateReservation()

        llm = _get_llm()
        from langchain_core.prompts import ChatPromptTemplate

        current = state.reservation
        extract_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Extract parking reservation fields from the user message. "
                    "Current known fields: "
                    f"first_name={current.first_name!r}, surname={current.surname!r}, "
                    f"license_plate={current.license_plate!r}, "
                    f"start_datetime={current.start_datetime!r}, "
                    f"end_datetime={current.end_datetime!r}. "
                    "Return ONLY a JSON object with keys: first_name, surname, license_plate, "
                    "start_datetime, end_datetime. Use null for fields not mentioned.",
                ),
                ("human", "{message}"),
            ]
        )
        import json

        result = llm.invoke(
            extract_prompt.format_messages(message=last_human.content)
        )
        try:
            raw = json.loads(result.content)
            for field in ("first_name", "surname", "license_plate", "start_datetime", "end_datetime"):
                val = raw.get(field)
                if val is not None:
                    setattr(state.reservation, field, val)
        except (json.JSONDecodeError, AttributeError):
            pass
    except Exception as exc:
        logger.error("reservation_collector_node failed: %s", exc)
        state.error = str(exc)
    return state


def reservation_validator_node(state: ConversationState) -> ConversationState:
    """Validate the current reservation draft and prompt for missing fields."""
    try:
        from chatbot.reservation.validator import validate_reservation

        if state.reservation is None:
            state.response_draft = "Let's start your reservation. What is your first name?"
            return state

        errors = validate_reservation(state.reservation)
        if errors:
            state.response_draft = "Please provide: " + "; ".join(errors)
        else:
            state.reservation.status = "submitted"
            state.response_draft = (
                f"Your reservation has been submitted!\n"
                f"Name: {state.reservation.first_name} {state.reservation.surname}\n"
                f"Plate: {state.reservation.license_plate}\n"
                f"From: {state.reservation.start_datetime} to {state.reservation.end_datetime}"
            )
    except Exception as exc:
        logger.error("reservation_validator_node failed: %s", exc)
        state.error = str(exc)
        state.response_draft = "There was a problem processing your reservation."
    return state
