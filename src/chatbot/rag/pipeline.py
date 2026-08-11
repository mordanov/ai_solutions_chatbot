"""RAG chain: retrieve → context → LLM → response."""
from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from chatbot.config import settings

FALLBACK_MESSAGE = (
    "I don't have enough information to answer that question. "
    "Please contact the parking facility directly."
)

_SYSTEM = (
    "You are a helpful parking facility assistant. "
    "Answer the user's question using ONLY the context below. "
    "If the context does not contain the answer, respond with exactly: "
    f'"{FALLBACK_MESSAGE}"'
)

_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM),
        (
            "human",
            "Context:\n{context_text}\n\nQuestion: {question}",
        ),
    ]
)


def _format_context(chunks: list[Document]) -> str:
    return "\n\n".join(c.page_content for c in chunks) if chunks else ""


def build_rag_chain(llm: BaseChatModel):
    """Return a callable chain({"question": str, "context": list[Document]}) -> str."""

    def chain(inputs: dict) -> str:
        question: str = inputs["question"]
        context: list[Document] = inputs.get("context", [])
        context_text = _format_context(context)

        if not context_text.strip():
            return FALLBACK_MESSAGE

        prompt = _PROMPT.format_messages(context_text=context_text, question=question)
        response = llm.invoke(prompt)
        return response.content

    return chain


def get_default_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        openai_api_key=settings.openai_api_key,
        temperature=0,
    )


def get_embedder() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
