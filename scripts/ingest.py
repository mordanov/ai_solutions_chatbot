"""CLI: load parking docs from data/parking_info/ into Milvus."""
import sys
from pathlib import Path

# Make src/ importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chatbot.knowledge.vector_store import MilvusVectorStore
from chatbot.rag.ingestion import ingest_documents


def main() -> None:
    data_dir = Path(__file__).parent.parent / "data" / "parking_info"
    if not data_dir.exists():
        print(f"Error: {data_dir} does not exist.")
        sys.exit(1)

    print(f"Connecting to Milvus and ingesting documents from {data_dir} …")
    store = MilvusVectorStore()
    count = ingest_documents(data_dir, store)
    print(f"Done. {count} chunks indexed.")


if __name__ == "__main__":
    main()
