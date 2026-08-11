"""Load and chunk markdown documents, then insert them into the vector store."""
import uuid
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from chatbot.config import settings
from chatbot.knowledge.vector_store import VectorStorePort

_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)


def ingest_documents(source_dir: Path, vector_store: VectorStorePort) -> int:
    """Load .md files from source_dir, chunk, embed, and store.

    Returns the number of chunks inserted.
    """
    loader = DirectoryLoader(str(source_dir), glob="**/*.md", loader_cls=TextLoader)
    raw_docs = loader.load()

    chunks: list[Document] = []
    for doc in raw_docs:
        source = Path(doc.metadata.get("source", "unknown")).name
        section = Path(source).stem
        split = _SPLITTER.split_documents([doc])
        for idx, chunk in enumerate(split):
            chunk.metadata.update(
                {
                    "id": str(uuid.uuid4()),
                    "source": source,
                    "section": section,
                    "chunk_index": idx,
                }
            )
            chunks.append(chunk)

    if not chunks:
        return 0

    embedder = OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )
    embeddings = embedder.embed_documents([c.page_content for c in chunks])
    vector_store.add_documents(chunks, embeddings)
    return len(chunks)
