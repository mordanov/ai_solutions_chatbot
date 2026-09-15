from langchain_core.documents import Document

from chatbot.knowledge.vector_store import VectorStorePort


class ParkingRetriever:
    def __init__(self, vector_store: VectorStorePort, top_k: int = 5) -> None:
        self._store = vector_store
        self._top_k = top_k

    def retrieve(self, query: str, embedding: list[float]) -> list[Document]:
        return self._store.similarity_search(embedding, top_k=self._top_k)
