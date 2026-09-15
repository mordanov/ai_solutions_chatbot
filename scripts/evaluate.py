"""CLI: run RAG evaluation against eval/questions.json and print a report."""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chatbot.config import settings
from chatbot.evaluation.runner import run_evaluation
from chatbot.knowledge.vector_store import MilvusVectorStore
from chatbot.rag.pipeline import build_rag_chain, get_default_llm
from chatbot.rag.retriever import ParkingRetriever


def main() -> None:
    dataset = Path(__file__).parent.parent / "eval" / "questions.json"
    if not dataset.exists():
        print(f"Error: {dataset} not found.")
        sys.exit(1)

    store = MilvusVectorStore()
    retriever = ParkingRetriever(store, top_k=settings.retrieval_top_k)
    llm = get_default_llm()
    chain = build_rag_chain(llm)

    print("Running evaluation …")
    report = run_evaluation(dataset, retriever, chain)

    print("\n=== Evaluation Report ===")
    print(f"Questions evaluated : {len(report.results)}")
    print(f"Avg Recall@5        : {report.avg_recall:.3f}")
    print(f"Avg Precision@5     : {report.avg_precision:.3f}")
    print(f"Avg Latency (ms)    : {report.avg_latency_ms:.0f}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(__file__).parent.parent / "eval" / f"report_{ts}.json"
    rows = [
        {
            "question": r.question,
            "generated_response": r.generated_response,
            "recall_at_5": r.recall_at_5,
            "precision_at_5": r.precision_at_5,
            "latency_ms": r.latency_ms,
        }
        for r in report.results
    ]
    with open(out_path, "w") as f:
        json.dump(
            {
                "avg_recall_at_5": report.avg_recall,
                "avg_precision_at_5": report.avg_precision,
                "avg_latency_ms": report.avg_latency_ms,
                "results": rows,
            },
            f,
            indent=2,
        )
    print(f"\nFull report written to {out_path}")


if __name__ == "__main__":
    main()
