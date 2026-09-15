# Feature Specification: Admin Reservation Approval

**Feature Branch**: `002-admin-approval`  
**Created**: 2026-08-11  
**Status**: Draft  
**Input**: User description: "Human in the loop — admin reservation approval workflow"

## Clarifications

### Session 2026-08-11

- Q: How should the admin approval/rejection endpoint be secured? → A: Bearer token authentication — same admin token used in Stage 1 API.
- Q: After submitting reservation details, how does the user receive the admin's decision? → A: In-session polling — user is told "awaiting approval"; chatbot polls and delivers the decision when ready.
- Q: Which channel should be the primary admin notification method? → A: Email (SMTP) — system emails the admin with reservation details and approve/reject action links.
- Q: Can the user interact with the chatbot on other topics while their reservation is pending approval? → A: Free interaction — user can continue chatting; chatbot checks for a pending decision at the start of each user message and reports it if ready.
- Q: What should persist the pending reservation state between chat requests? → A: In-process store — module-level dictionary keyed by session ID, cleared on process restart.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Reservation Escalated to Admin (Priority: P1)

After a user has provided all required reservation details via the chatbot, the system automatically forwards the reservation request to an administrator for review and approval before it is finalised.

**Why this priority**: This is the core integration between the user-facing chatbot and the human administrator. Without it, no other part of the workflow can function.

**Independent Test**: Can be tested by submitting a complete reservation through the chatbot and verifying that an admin notification is dispatched with the correct details.

**Acceptance Scenarios**:

1. **Given** a user has provided all required reservation fields (name, licence plate, dates), **When** the chatbot validates the fields as complete, **Then** the system forwards the reservation details to the administrator and informs the user that their request is awaiting admin approval.
2. **Given** the reservation request has been forwarded, **When** the admin notification is sent, **Then** the notification contains the full reservation details (first name, surname, licence plate, start date/time, end date/time) and a mechanism to approve or reject.
3. **Given** the admin notification cannot be delivered (channel unavailable), **When** the forwarding attempt fails, **Then** the chatbot informs the user that submission failed and they should try again later.

---

### User Story 2 — Admin Reviews and Decides (Priority: P2)

An administrator receives a reservation request notification and can approve or reject it through a dedicated interface.

**Why this priority**: The admin decision is the central human-in-the-loop action. The system has no value without this step being functional.

**Independent Test**: Can be tested by calling the admin decision endpoint directly with an approval or rejection payload and verifying the system records the outcome correctly.

**Acceptance Scenarios**:

1. **Given** a pending reservation request has been forwarded, **When** an admin submits an approval decision, **Then** the system records the decision as "approved" and proceeds to notify the user.
2. **Given** a pending reservation request has been forwarded, **When** an admin submits a rejection decision with an optional reason, **Then** the system records the decision as "rejected" and proceeds to notify the user with the reason.
3. **Given** a pending reservation, **When** an admin attempts to decide on a request that has already been decided or has timed out, **Then** the system returns an appropriate error indicating the request is no longer actionable.

---

### User Story 3 — User Receives Decision (Priority: P2)

After the administrator makes a decision, the user is informed of the outcome within the same chat session. After submitting, the chatbot immediately informs the user their request is awaiting approval and continues to poll for a decision, delivering the result as a new chat message when available.

**Why this priority**: Closing the loop with the user is essential for the workflow to be useful. Without it, users would have no way to know whether their reservation was accepted.

**Independent Test**: Can be tested by triggering a simulated admin decision and verifying that the chatbot session receives and displays the correct outcome message.

**Acceptance Scenarios**:

1. **Given** an admin has approved a reservation, **When** the decision is relayed back to the chatbot, **Then** the user sees a confirmation message with their reservation details and approval status.
2. **Given** an admin has rejected a reservation, **When** the decision is relayed back to the chatbot, **Then** the user sees a rejection message including any reason provided by the admin.
3. **Given** no admin decision is received within the configured timeout period, **When** the timeout elapses, **Then** the user is informed that their request could not be processed in time and is invited to resubmit.

---

### Edge Cases

- What happens when the admin notification channel is unavailable at forwarding time?
- How does the system handle duplicate approval/rejection calls for the same reservation?
- What if the user disconnects or the session expires before the admin decision is returned?
- How does the system behave when multiple reservations are pending simultaneously?
- What happens if the admin approves a request after the timeout has already informed the user?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST forward completed reservation requests to the admin agent automatically upon successful field validation.
- **FR-002**: The admin agent MUST dispatch a notification to the administrator containing all reservation fields and a response mechanism (approve/reject).
- **FR-003**: The administrator MUST be able to approve a reservation request through the provided response mechanism; the endpoint MUST require a valid bearer token (the same admin token used by the Stage 1 API).
- **FR-004**: The administrator MUST be able to reject a reservation request, optionally supplying a reason; the endpoint MUST require a valid bearer token.
- **FR-005**: The system MUST relay the administrator's decision (approved or rejected, with optional reason) back to the chatbot agent.
- **FR-006**: The chatbot MUST present the admin's decision to the user with a human-readable confirmation or rejection message delivered as a new chat message in the same session.
- **FR-010**: After forwarding a reservation, the chatbot MUST immediately inform the user that their request is pending admin approval. On each subsequent user message, the chatbot MUST first check whether a pending decision has arrived; if it has, the decision MUST be reported to the user before processing their new query. The user MUST be free to continue chatting on any topic while approval is pending.
- **FR-007**: The system MUST enforce a configurable timeout; if no admin decision is received within the timeout, the user MUST be notified that their request has expired.
- **FR-008**: The admin agent MUST NOT allow the same reservation request to be decided more than once; duplicate decision attempts MUST return an appropriate error.
- **FR-009**: The admin agent MUST send an email notification to the administrator via SMTP containing all reservation fields and unique approve/reject action links. SMTP connection settings (host, port, credentials, recipient address) MUST be configurable via environment variables. HTTP webhook remains a supported alternative channel.

### Key Entities

- **ReservationRequest**: A pending request awaiting admin review. Attributes: unique request ID, user session ID, first name, surname, licence plate, start date/time, end date/time, submitted timestamp, status (pending / approved / rejected / expired).
- **AdminNotification**: The message dispatched to the administrator. Contains all reservation fields plus a unique action URL or token.
- **ApprovalDecision**: The administrator's response. Attributes: request ID, decision (approved / rejected), optional reason, decided timestamp.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A validated reservation is forwarded to the admin agent within 3 seconds of the user completing field entry.
- **SC-002**: The administrator receives a notification within 10 seconds of the reservation being submitted.
- **SC-003**: The user receives the outcome of the admin's decision within 5 seconds of the decision being recorded.
- **SC-004**: The system correctly expires and notifies the user for 100% of requests where no admin decision arrives within the configured timeout window.
- **SC-005**: Duplicate decision attempts on the same request are rejected 100% of the time with an appropriate error.

## Assumptions

- The administrator is a human operator who receives reservation notifications via email (SMTP). A local mock SMTP server (e.g., MailHog) is sufficient for development and demo environments. HTTP webhook is a supported alternative but is not the primary showcase channel.
- The admin decision interface is a bearer-token-protected HTTP endpoint using the same admin token as the Stage 1 API; a dedicated admin UI is out of scope for this stage.
- Pending reservation state (request ID, session ID, status) is held in an in-process dictionary keyed by session ID. This store is cleared on process restart; durable cross-process persistence is out of scope for this stage.
- The chatbot (first agent) and admin agent (second agent) run within the same deployed system and communicate via internal interfaces or shared state.
- The default timeout for awaiting an admin decision is 5 minutes; this value is configurable via environment variable.
- Only one administrator role exists; role-based access control is out of scope for this stage.
- The chatbot delivers the admin decision via in-session polling; the user sees a "pending" message immediately and receives the outcome as a follow-up chat message when the admin decides. Async notification delivery to the user (e.g., SMS, email) is out of scope for this stage.
