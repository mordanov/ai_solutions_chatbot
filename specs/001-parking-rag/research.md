# Research: Parking Chatbot RAG Foundation

**Branch**: `001-parking-rag` | **Date**: 2026-08-11

---

## Decision 1 — LLM Selection

**Decision**: OpenAI GPT-4o (default); Claude claude-sonnet-5 as drop-in alternative.

**Rationale**: GPT-4o has first-class LangChain integration, strong structured-output
support (required for reservation field extraction), and a well-established track record
in RAG applications. The Anthropic Claude SDK is also fully supported by LangChain via
`langchain-anthropic`; switching requires only a config change, no code rewrites.

**Alternatives considered**:
- Claude claude-sonnet-5: excellent reasoning, slightly higher latency; use when
  Anthropic is preferred by the operator.
- Local models via Ollama: avoids API costs but requires GPU and complicates CI setup.

---

## Decision 2 — Embedding Model

**Decision**: `text-embedding-3-small` (OpenAI), 1536 dimensions.

**Rationale**: Best cost-to-quality ratio for retrieval tasks. Supports batch embedding,
which speeds up ingestion. Produces smaller index than `text-embedding-3-large` while
retaining sufficient recall for the parking domain (small corpus).

**Alternatives considered**:
- `text-embedding-3-large` (3072 dims): higher quality but 5× cost, unnecessary for
  a domain with a limited number of distinct facts.
- `sentence-transformers/all-MiniLM-L6-v2`: free, runs locally; acceptable accuracy
  for offline/air-gapped deployment but requires extra dependency and slower ingestion.

---

## Decision 3 — Vector Database

**Decision**: Milvus (Milvus Lite for dev/test, Milvus Standalone via Docker for
production-like environments).

**Rationale**: Only option from the constitution's approved list (Milvus, Pinecone,
Weaviate) that runs fully locally without requiring a cloud account, which is important
for reproducible CI and offline development. LangChain has a first-class `Milvus`
vector store integration. Milvus Lite can run in-process (no Docker) for unit tests.

**Alternatives considered**:
- Pinecone: managed, zero-ops, excellent DX, but requires cloud account and internet.
  Selected as the recommended production upgrade path.
- Weaviate: strong GraphQL API, but heavier setup and less straight-forward Docker
  Compose for a single-node deployment.

---

## Decision 4 — Dynamic Data Storage

**Decision**: PostgreSQL via SQLAlchemy ORM (SQLite for dev/test).

**Rationale**: Prices, opening hours, and availability are structured, frequently
queried, and require ACID guarantees. A relational database is the natural fit.
SQLAlchemy enables the same model code to target SQLite (tests, dev) and PostgreSQL
(staging, production) by changing only the connection string.

**Alternatives considered**:
- Redis: fast, but schema-less; overkill for a small dataset and harder to reason
  about for structured parking rates.
- MongoDB: unnecessary document flexibility for well-defined structured records.

---

## Decision 5 — Guard Rails Mechanism

**Decision**: Two-layer output filter.
- Layer 1: Microsoft Presidio for PII/sensitive entity detection (names, licence plates,
  phone numbers, emails) in outgoing responses.
- Layer 2: Rule-based blocklist covering credential patterns (API key shapes, JWT tokens)
  and injection probes.

**Rationale**: Presidio is a production-grade open-source library designed exactly for
this purpose. It does not require training a custom model. The rule-based layer adds
deterministic coverage for patterns Presidio may not cover (e.g., custom secrets,
prompt-injection phrases). The combination gives both ML-based recall and rule-based
precision.

**Alternatives considered**:
- Custom transformer classifier: high accuracy but requires labelled training data and
  inference infrastructure. Too heavyweight for Stage 1.
- LLM-based self-check ("Does this response contain sensitive data?"): probabilistic,
  adds latency and cost; not reliable enough as the sole mechanism.

---

## Decision 6 — RAG Chunking Strategy

**Decision**: Recursive character text splitter, chunk size 512 tokens, overlap 50 tokens.

**Rationale**: The parking domain documents (FAQ pages, rule sheets, location pages)
are short prose. A 512-token chunk captures a complete factual paragraph while
remaining small enough to give the retriever precise matches. The 50-token overlap
prevents context loss at chunk boundaries.

**Alternatives considered**:
- Sentence splitter: more semantically clean but requires sentence-boundary detection
  and produces variable-length chunks that complicate embedding batching.
- Fixed 256-token chunks: more precise retrieval but risks splitting related sentences
  and increasing index size without proportional quality gain.

---

## Decision 7 — Retrieval Parameters

**Decision**: Dense vector search, top-k = 5. No hybrid search in Stage 1.

**Rationale**: The static corpus is small (< 200 documents expected). Dense-only
retrieval is sufficient to achieve the SC-002/SC-003 targets (Recall@5 ≥ 0.80,
Precision@5 ≥ 0.75). Hybrid BM25 + dense search can be introduced in Stage 4
if evaluation shows a recall gap.

---

## Decision 8 — UI Layer

**Decision**: Streamlit for interactive demo; FastAPI REST endpoint as the production
interface alongside it.

**Rationale**: Streamlit provides a zero-boilerplate conversational UI that is ideal
for evaluation and demos. FastAPI exposes the same chatbot as a REST API for
integration with other clients and for the admin workflow in later stages. Both can
run from the same codebase.

---

## Decision 9 — Evaluation Framework

**Decision**: Custom metric computation (no external RAGAS dependency in Stage 1).
Metrics: Recall@K (K=5), Precision@K (K=5), end-to-end latency (ms).
Evaluation dataset: manually curated JSON file with question–expected-answer–
relevant-chunk-ids triples (minimum 20 entries).

**Rationale**: RAGAS is powerful but adds a dependency on a secondary LLM call per
evaluation run, increasing cost and complexity. For Stage 1, computing overlap between
retrieved chunk IDs and ground-truth relevant IDs is sufficient to validate the
retrieval pipeline. RAGAS can be added in Stage 4 for answer-faithfulness scoring.
