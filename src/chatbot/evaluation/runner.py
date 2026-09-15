"""Evaluation orchestrator: run RAG pipeline over a QA dataset and compute metrics."""
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from chatbot.evaluation.metrics import precision_at_k, recall_at_k

logger = logging.getLogger(__name__)


@dataclass
class QuestionResult:
    question: str
    expected_answer: str
    relevant_chunk_ids: list[str]
    retrieved_chunk_ids: list[str]
    generated_response: str
    recall_at_5: float
    precision_at_5: float
    latency_ms: int


@dataclass
class EvaluationReport:
    results: list[QuestionResult] = field(default_factory=list)

    @property
    def avg_recall(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.recall_at_5 for r in self.results) / len(self.results)

    @property
    def avg_precision(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.precision_at_5 for r in self.results) / len(self.results)

    @property
    def avg_latency_ms(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.latency_ms for r in self.results) / len(self.results)


def run_evaluation(dataset_path: Path, retriever, rag_chain) -> EvaluationReport:
    """Run each question through retriever + chain and compute Recall@5/Precision@5.

    Args:
        dataset_path: Path to questions.json
        retriever: object with .retrieve(question, embedding) -> list[Document]
        rag_chain: callable({"question": str, "context": list[Document]}) -> str
    """
    from langchain_openai import OpenAIEmbeddings

    from chatbot.config import settings

    with open(dataset_path) as f:
        questions = json.load(f)

    embedder = OpenAIEmbeddings(
        model=settings.embedding_model, openai_api_key=settings.openai_api_key
    )

    report = EvaluationReport()
    for item in questions:
        question = item["question"]
        expected = item.get("expected_answer", "")
        relevant_ids = item.get("relevant_chunk_ids", [])

        start = time.monotonic()
        try:
            embedding = embedder.embed_query(question)
            chunks = retriever.retrieve(question, embedding)
            response = rag_chain({"question": question, "context": chunks})
        except Exception as exc:
            logger.error("Evaluation failed for question %r: %s", question, exc)
            response = ""
            chunks = []
        latency_ms = int((time.monotonic() - start) * 1000)

        retrieved_ids = [c.metadata.get("id", "") for c in chunks]
        report.results.append(
            QuestionResult(
                question=question,
                expected_answer=expected,
                relevant_chunk_ids=relevant_ids,
                retrieved_chunk_ids=retrieved_ids,
                generated_response=response,
                recall_at_5=recall_at_k(retrieved_ids, relevant_ids, k=5),
                precision_at_5=precision_at_k(retrieved_ids, relevant_ids, k=5),
                latency_ms=latency_ms,
            )
        )

    return report
