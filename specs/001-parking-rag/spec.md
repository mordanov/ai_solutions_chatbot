# Feature Specification: Parking Chatbot RAG Foundation

**Feature Branch**: `001-parking-rag`
**Created**: 2026-08-11
**Status**: Draft
**Input**: User description: "@requirements/spec_01_rag.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ask a Parking Question (Priority: P1)

A visitor to the parking facility wants to know general information such as location,
opening hours, available services, or the booking process. They open the chatbot and
ask a natural-language question. The chatbot answers accurately using information from
the knowledge base without fabricating details.

**Why this priority**: This is the chatbot's primary value proposition. All other
capabilities depend on being able to reliably answer factual questions first.

**Independent Test**: Can be fully tested by submitting a set of representative
parking-related questions and verifying that answers are grounded in the knowledge
base and factually accurate.

**Acceptance Scenarios**:

1. **Given** the knowledge base contains parking location information, **When** a user
   asks "Where is the parking located?", **Then** the chatbot returns the correct
   address without adding invented details.
2. **Given** the knowledge base contains opening hours, **When** a user asks "What
   are your opening hours?", **Then** the chatbot returns the correct hours.
3. **Given** a question falls outside the knowledge base, **When** the user asks it,
   **Then** the chatbot states it does not have enough information rather than guessing.

---

### User Story 2 — Ask About Prices or Availability (Priority: P2)

A driver wants to know current parking prices or whether a space is available before
deciding to visit. They ask the chatbot and receive an up-to-date answer reflecting
the current state of the parking facility.

**Why this priority**: Prices and availability change over time, making them the most
time-sensitive information the chatbot must serve. Accuracy here directly affects
trust.

**Independent Test**: Can be fully tested by querying the chatbot for current prices
and availability while the underlying data source holds known values, and verifying
the chatbot returns those exact values.

**Acceptance Scenarios**:

1. **Given** the current hourly rate is stored in the data source, **When** a user
   asks "How much does parking cost per hour?", **Then** the chatbot returns the
   current rate.
2. **Given** real-time availability data is accessible, **When** a user asks "Are
   there any free spaces?", **Then** the chatbot returns the current availability
   status.
3. **Given** availability data cannot be retrieved, **When** a user asks, **Then**
   the chatbot acknowledges it cannot confirm current availability rather than
   guessing.

---

### User Story 3 — Start a Reservation Request (Priority: P3)

A user decides to reserve a parking space and asks the chatbot to help. The chatbot
guides them through providing their first name, surname, license plate, and desired
reservation period, collecting each piece of information step by step.

**Why this priority**: Reservation collection is a workflow that builds on the
information-retrieval foundation. It requires the chatbot to be conversational and
stateful, which is more complex.

**Independent Test**: Can be fully tested by walking through a reservation dialogue
and verifying the chatbot collects all required fields, validates each one, and
stores the complete request for further processing.

**Acceptance Scenarios**:

1. **Given** a user says "I'd like to reserve a spot", **When** the chatbot engages,
   **Then** it asks for each required field (first name, surname, license plate,
   start time, end time) in a logical conversational sequence.
2. **Given** the user provides an invalid license plate format, **When** they submit
   it, **Then** the chatbot asks them to correct it without losing previously entered
   valid data.
3. **Given** all required fields are collected and valid, **When** the user confirms,
   **Then** the chatbot acknowledges the request has been submitted for review.

---

### User Story 4 — Guard Rails Block Sensitive Data (Priority: P2)

An adversarial or accidental query attempts to extract private information such as
other users' reservation records, administrator credentials, or internal system
details. The chatbot detects and blocks the disclosure before responding.

**Why this priority**: Alongside prices/availability, data protection is non-negotiable
for a system handling personal and operational data. A breach in this area is a
compliance failure regardless of how well other features work.

**Independent Test**: Can be fully tested by submitting a set of boundary-probing
prompts and verifying the chatbot refuses to disclose private records, credentials,
or internal metadata in all cases.

**Acceptance Scenarios**:

1. **Given** a user asks for "all reservations made today", **When** the chatbot
   processes the request, **Then** it refuses to return other users' reservation data.
2. **Given** a user attempts prompt injection to reveal the system prompt, **When**
   the chatbot processes the request, **Then** it does not expose internal
   configuration or credentials.
3. **Given** a query contains no sensitive intent, **When** the chatbot processes it,
   **Then** guard rails do not produce false positives that block legitimate answers.

---

### Edge Cases

- What happens when the knowledge base returns no matching chunks for a question?
  → Chatbot should explicitly state insufficient information.
- What happens when the dynamic data source (availability / prices) is temporarily
  unavailable? → Chatbot should acknowledge the data is unavailable rather than
  serving stale or fabricated values.
- What happens when a user submits a very long or malformed message?
  → Guard rails and input limits should prevent errors or unexpected behavior.
- What happens when a user asks a question completely unrelated to parking?
  → Chatbot should politely redirect to parking topics rather than answering
  out-of-scope questions.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST answer natural-language questions about parking using
  information retrieved from a knowledge base.
- **FR-002**: The system MUST serve static parking information (general details,
  location, booking process) from a dedicated store optimised for semantic search.
- **FR-003**: The system MUST serve dynamic parking information (current prices,
  working hours, space availability) from a data source that reflects the current
  operational state.
- **FR-004**: The system MUST NOT present the language model's own assumptions as
  factual parking information when the knowledge base contains relevant data.
- **FR-005**: The system MUST collect the following reservation fields interactively:
  first name, surname, car/license plate number, reservation start, reservation end.
- **FR-006**: The system MUST validate each collected reservation field and re-prompt
  without losing previously provided valid data when a field is invalid.
- **FR-007**: The system MUST apply guard rails that prevent disclosure of: other
  users' personal data or reservation records; administrator credentials; internal
  system configuration; API keys or secrets.
- **FR-008**: The guard rails MUST use an automated detection mechanism (such as a
  pre-trained NLP classifier or rule-based filter) rather than relying solely on
  the language model's own judgement.
- **FR-009**: The system MUST measure and record end-to-end response latency for
  each user interaction.
- **FR-010**: The system MUST evaluate retrieval quality using at minimum Recall@K
  and Precision metrics on a representative set of parking questions.
- **FR-011**: Evaluation results MUST be produced as a documented report.

### Key Entities

- **ParkingKnowledgeBase**: Stores static parking facts (general info, location,
  services, booking process, parking rules). Supports semantic similarity search.
- **ParkingOperationalData**: Stores dynamic operational state (current prices,
  working hours per day, real-time or near-real-time space availability counts).
- **ConversationSession**: Tracks the current dialogue state including context
  window, collected reservation fields, and workflow stage for a single user session.
- **ReservationDraft**: In-progress reservation record holding: first name, surname,
  license plate, start datetime, end datetime, validation status.
- **EvaluationRecord**: Stores question–expected-answer pairs, retrieved context,
  model response, and computed retrieval metrics for offline evaluation.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can ask any of ten representative parking questions and receive
  a factually correct, grounded answer in under 5 seconds on average.
- **SC-002**: Retrieval Recall@5 is 0.80 or above on the evaluation question set.
- **SC-003**: Retrieval Precision@5 is 0.75 or above on the evaluation question set.
- **SC-004**: The chatbot successfully guides a user through the complete reservation
  data-collection dialogue (all five fields) with no data loss on the first attempt
  when all inputs are valid.
- **SC-005**: Guard rails block 100% of a defined set of boundary-probing prompts
  designed to extract private records or credentials, with a false-positive rate
  below 5% on legitimate parking queries.
- **SC-006**: An evaluation report is produced documenting latency measurements and
  retrieval quality metrics.

---

## Assumptions

- The parking facility's static information (location, general description, booking
  process, rules) is available as structured or semi-structured documents that can
  be loaded into the knowledge base at setup time.
- Dynamic data (prices, working hours, availability) is accessible via a structured
  data store that can be queried at runtime; exact format will be determined during
  planning.
- Reservation collection in this stage ends at confirming the draft to the user;
  administrator approval is out of scope for Stage 1 (covered in Stage 3).
- The chatbot interaction mode is text-based; voice or multi-modal input is out of
  scope.
- A representative evaluation question set (at minimum 20 question–answer pairs) will
  be assembled during development; the spec assumes this is feasible.
- Guard rails are applied at the output layer before the response is returned to the
  user; the exact detection model or rule set will be selected during planning.
- The system is a single-tenant deployment for one parking facility; multi-tenant
  isolation is out of scope.
