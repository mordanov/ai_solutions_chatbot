# Stage 4 Retrospective — LangGraph Pipeline Orchestration

**Branch**: `004-langgraph-orchestration`  
**Date**: 2026-08-12  
**Workflow**: speckit (specify → plan → tasks → implement)

---

## What Was Done

### Feature 004 — LangGraph Pipeline Orchestration

The LangGraph pipeline connecting all four stages was already fully implemented across features 001–003. This feature's actual scope was **Stage 4 hardening**: closing test coverage gaps, adding end-to-end pipeline integration tests, fixing CI, and updating documentation.

| Component | File(s) | Description |
|-----------|---------|-------------|
| CI fix | `.github/workflows/ci.yml` | Added `python -m spacy download en_core_web_lg` step; without it, guard-rails tests would fail in CI on every PR |
| Graph routing tests | `tests/unit/test_workflow_graph.py` | 8 new tests covering all three conditional routing functions (`_route_after_intent`, `_route_after_reservation_validator`, `_route_after_pending_check`) — previously zero coverage |
| Node tests — RAG | `tests/unit/test_workflow_nodes.py` | `retrieve_and_generate` ×2: success path (mocked LLM + retriever) and fallback on Milvus error |
| Node tests — dynamic data | `tests/unit/test_workflow_nodes.py` | `dynamic_data_node` ×2: pricing intent and hours intent, both with mocked repository |
| Node tests — out-of-scope | `tests/unit/test_workflow_nodes.py` | `out_of_scope_node` ×2: response draft set; reservation not mutated |
| Node tests — reservation collector | `tests/unit/test_workflow_nodes.py` | `reservation_collector_node` ×2: full JSON extraction; no-human-message guard |
| Node tests — approval | `tests/unit/test_workflow_nodes.py` | `approval_request_node` ×2: success path; service failure sets error |
| Node tests — guard rails | `tests/unit/test_workflow_nodes.py` | `guard_rails_node` ×2: PII scan bypass for approval messages; blocked content on rule hit |
| Node tests — pending check | `tests/unit/test_workflow_nodes.py` | `pending_check_node` ×3: approved; expired; rejected |
| Node tests — respond | `tests/unit/test_workflow_nodes.py` | `respond` ×2: AIMessage appended from `response_final`; fallback when both drafts are None |
| Approval pipeline integration test | `tests/unit/test_pipeline_integration.py` | Full path: POST `/chat` (reservation intent, all fields) → POST `/admin/approve` → POST `/chat` (same session) → "approved" in response; `write_record` called once with correct name/car_number |
| Rejection pipeline integration test | `tests/unit/test_pipeline_integration.py` | Same path with reject: `write_record` not called; "rejected"/"not approved" in response |
| README | `README.md` | Evaluation Results section updated with run instructions, expected output format, and note on Milvus dependency |
| Spec artifacts | `specs/004-langgraph-orchestration/` | spec.md, plan.md, research.md, data-model.md, quickstart.md, contracts/pipeline-test-contract.md, checklists/requirements.md, tasks.md |
| Agent context | `CLAUDE.md` | Updated speckit pointer from `003-mcp-reservation-storage/plan.md` to `004-langgraph-orchestration/plan.md` |
| **Total unit tests** | — | **98 passing** (up from 69, +29 new) |

---

## What Was NOT Done

| Item | Reason | Impact |
|------|--------|--------|
| Actual evaluation numbers in README | `pymilvus` is not installed in the dev environment; `scripts/evaluate.py` requires a live Milvus instance | README documents how to run evaluation and the expected format; numbers are not fabricated |
| Load/performance testing | Requires a live stack (Milvus, PostgreSQL, SMTP, running API); not achievable in unit CI | Documented as out-of-scope for automated CI in `research.md` |
| Architecture diagram (visual) | README has ASCII art; a proper diagram (e.g. Mermaid or PNG) was not added | The ASCII diagram is functional; a visual upgrade was not in the task list |
| PowerPoint presentation | Extra credit item from the requirements; no tooling available in this session | Can be created manually from the spec and README content |
| `speckit-git-commit` after each phase | The optional after-hooks were not triggered; changes were not committed mid-session | All changes are uncommitted on the branch; a single commit at the end is fine |

---

## What Was Good

**The pipeline was already done — and the plan reflected that honestly.**  
The most important output of the `/speckit-plan` phase was recognizing that the LangGraph orchestration was complete and that feature 004 was really Stage 4 hardening. A naive implementation attempt would have tried to re-implement the graph. The plan was honest about scope, which kept the implementation focused.

**Graph routing tests were genuinely missing and now cover all decision points.**  
`workflow/graph.py` had zero automated tests. The three routing functions (`_route_after_intent`, `_route_after_reservation_validator`, `_route_after_pending_check`) are the wiring that connects all the nodes; a wrong routing condition would silently misroute messages. 8 deterministic unit tests — no LLM, no mocks — now cover every branch.

**End-to-end pipeline tests exercise the real integration path.**  
The two pipeline tests in `test_pipeline_integration.py` are the highest-value tests added: they verify that a user message actually flows through the LangGraph graph, creates an `ApprovalRequest` in the store, gets approved (or rejected), and that the user's next message receives the correct notification. These tests are fast (< 2s) and require no external services.

**All 9 workflow nodes now have ≥ 2 unit tests each.**  
Before this session: only `route_intent` and `reservation_validator_node` were covered (4 tests). After: all 9 nodes have coverage. This satisfies the constitution's "at least two automated tests per application module" requirement for `workflow/nodes.py`.

**The `guard_rails_node` bypass test caught a subtle correctness invariant.**  
The test verifying that PII scanning is bypassed when `approval_request_id` is set (`test_guard_rails_node_bypasses_pii_scan_for_approval_messages`) documents an intentional design decision that was previously invisible — approval messages legitimately contain user names and plate numbers that would otherwise be filtered. Without this test, a future refactor of the guard-rails logic could silently break reservation approval notifications.

---

## What Was Bad

**The mock strategy for `_get_llm` is fragile.**  
The pipeline integration tests patch `chatbot.workflow.nodes._get_llm` with a mock whose `invoke.side_effect` is a list: first call returns `"reservation"`, second returns the JSON. This works because `route_intent` and `reservation_collector_node` each call `_get_llm()` once in the expected order. If the graph routing changes (e.g. `pending_check_node` gains an LLM call, or the order of invocations shifts), the `side_effect` list will produce wrong responses and the tests will fail with confusing errors. The failure mode is not "assert fails", it is "wrong LLM response causes wrong routing".

**`test_dynamic_data_node_pricing` patches at the wrong level.**  
`dynamic_data_node` does `from chatbot.data.repository import ParkingRepository` inside the function, but the test patches `chatbot.data.repository.ParkingRepository`. This works because the import path is the same, but it's subtly dependent on the import happening at call time rather than at module import time. If the import ever moves to the top of `nodes.py`, the patch target would need to change to `chatbot.workflow.nodes.ParkingRepository`.

**README evaluation section provides format but no numbers.**  
The task said "run `evaluate.py` and populate with actual values." The script couldn't run without Milvus. The README now has instructions and a format template but no concrete numbers. For a graded submission, reviewers will see a placeholder rather than actual measured retrieval quality.

---

## What Could Be Done Better

**Use a state-machine mock for the LLM rather than a `side_effect` list.**  
Instead of relying on call order, the mock could inspect the prompt to decide what to return. A simple pattern:

```python
def _smart_llm_mock(prompt_messages, *args, **kwargs):
    system = next((m.content for m in prompt_messages if isinstance(m, SystemMessage)), "")
    if "Classify" in system:           # route_intent prompt
        return MagicMock(content="reservation")
    if "Extract parking reservation" in system:  # reservation_collector prompt
        return MagicMock(content=_RESERVATION_JSON)
    return MagicMock(content="")

mock_llm.invoke.side_effect = _smart_llm_mock
```

This makes the test robust to graph changes and documents the intent of each mock response explicitly.

**Add a `@pytest.mark.integration` tag to `test_pipeline_integration.py`.**  
Currently these tests live in `tests/unit/` and run in CI without external services. That is correct and intentional, but the file name (`test_pipeline_integration.py`) is misleading — they are unit tests with a large scope, not integration tests in the Docker sense. Either rename the file to `test_workflow_e2e.py` or add the `integration` mark but keep them in `tests/unit/` with a note explaining that the mark means "wide scope, not docker-required."

**Run `scripts/evaluate.py` in CI against a mock retriever.**  
The evaluation script could accept a `--mock` flag that substitutes the Milvus retriever with a deterministic stub. This would allow Recall@5/Precision@5 to be computed in CI using a fixed QA dataset — giving real numbers in the README that are reproducible without Docker.

**Generate the PowerPoint presentation programmatically.**  
The spec and plan contain all the content needed for a presentation: architecture diagram, stage descriptions, workflow graph, demo walkthrough. A Marp Markdown file (as used in `specs/002-admin-approval/presentation.md`) would produce a PDF/PPTX from the same source material and could be committed as a deliverable.

**Pre-seed the `PendingStore` fixture with a factory function.**  
Both `test_pipeline_integration.py` and `test_approval_api.py` have their own `_seed`/`_submit_reservation` helpers. A shared `conftest.py` fixture that creates an `ApprovalRequest` directly in the store (bypassing SMTP) would eliminate the duplication and make both test files simpler.
