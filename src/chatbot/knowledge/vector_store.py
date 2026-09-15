"""VectorStorePort abstraction and MilvusVectorStore implementation."""
from abc import ABC, abstractmethod
from typing import Any

from langchain_core.documents import Document

from chatbot.config import settings

_EMBEDDING_DIM = 1536
_COLLECTION = settings.milvus_collection


class VectorStorePort(ABC):
    """Minimal interface for semantic search over parking knowledge."""

    @abstractmethod
    def similarity_search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[Document]:
        ...

    @abstractmethod
    def add_documents(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> None:
        ...

    @abstractmethod
    def drop_collection(self) -> None:
        ...


class MilvusVectorStore(VectorStorePort):
    """Thin wrapper around PyMilvus for the parking_knowledge collection."""

    def __init__(self, uri: str = settings.milvus_uri, collection_name: str = _COLLECTION) -> None:
        from pymilvus import connections  # lazy import — keeps unit tests pymilvus-free

        self._collection_name = collection_name
        connections.connect(alias="default", uri=uri)
        self._collection = self._get_or_create_collection()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create_collection(self):
        from pymilvus import Collection, utility

        if utility.has_collection(self._collection_name):
            col = Collection(self._collection_name)
            col.load()
            return col
        return self._create_collection()

    def _create_collection(self):
        from pymilvus import Collection, CollectionSchema, DataType, FieldSchema

        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="chunk_index", dtype=DataType.INT32),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=_EMBEDDING_DIM),
        ]
        schema = CollectionSchema(fields, description="Parking knowledge base")
        col = Collection(name=self._collection_name, schema=schema)
        col.create_index(
            "embedding",
            {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}},
        )
        col.load()
        return col

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    def similarity_search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[Document]:
        results = self._collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 10}},
            limit=top_k,
            output_fields=["id", "content", "source", "section", "chunk_index"],
        )
        docs: list[Document] = []
        for hits in results:
            for hit in hits:
                docs.append(
                    Document(
                        page_content=hit.entity.get("content", ""),
                        metadata={
                            "id": hit.entity.get("id"),
                            "source": hit.entity.get("source"),
                            "section": hit.entity.get("section"),
                            "chunk_index": hit.entity.get("chunk_index"),
                            "score": hit.score,
                        },
                    )
                )
        return docs

    def add_documents(
        self, documents: list[Document], embeddings: list[list[float]]
    ) -> None:
        if not documents:
            return
        data: dict[str, list[Any]] = {
            "id": [],
            "content": [],
            "source": [],
            "section": [],
            "chunk_index": [],
            "embedding": [],
        }
        for doc, emb in zip(documents, embeddings):
            data["id"].append(doc.metadata["id"])
            data["content"].append(doc.page_content[:4096])
            data["source"].append(doc.metadata.get("source", ""))
            data["section"].append(doc.metadata.get("section", ""))
            data["chunk_index"].append(int(doc.metadata.get("chunk_index", 0)))
            data["embedding"].append(emb)
        self._collection.insert(list(data.values()))
        self._collection.flush()

    def drop_collection(self) -> None:
        from pymilvus import utility

        if utility.has_collection(self._collection_name):
            utility.drop_collection(self._collection_name)
