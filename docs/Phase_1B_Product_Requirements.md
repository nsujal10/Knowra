# Phase 1B: Product Requirements

## 1. Core Use Cases

| ID        | Use Case                          | Primary Actor | Priority |
| :---      | :---                              | :---          | :---     |
| **UC-01** | Upload meeting recording          | Employee      | P0       |
| **UC-02** | Transcribe meeting                | System        | P0       |
| **UC-03** | Identify speakers                 | System        | P0       |
| **UC-04** | Generate summary                  | System        | P0       |
| **UC-05** | Extract decisions                 | System        | P0       |
| **UC-06** | Extract action items              | System        | P0       |
| **UC-07** | Extract risks                     | System        | P1       |
| **UC-08** | Search meetings                   | Employee      | P0       |
| **UC-09** | Ask AI questions                  | Employee      | P0       |
| **UC-10** | View citations & source grounding | Employee      | P0       |
| **UC-11** | Track & assign actions            | Manager       | P1       |
| **UC-12** | View organizational decisions     | Manager       | P1       |
| **UC-13** | Manage users & orgs               | Admin         | P0       |
| **UC-14** | Manage roles & permissions        | Admin         | P0       |
| **UC-15** | Audit activity & access logs      | Admin         | P1       |

---

## 2. Key User Stories & Acceptance Criteria

### US-001: Upload and Process Meeting Recording
**As an** Employee,  
**I want to** upload a recorded meeting file (audio or video),  
**So that** the system can automatically transcribe, diarize, and extract key insights without manual overhead.

#### Acceptance Criteria
```gherkin
Scenario: Successful upload and asynchronous processing initiation
  Given an authenticated user is on the meeting upload page
  When the user selects a valid 45-minute MP4 file (size <= 500 MB) and submits the upload form
  Then the system validates the file format and payload size
  And stores the raw file in secure object storage
  And creates a meeting record with status "PENDING"
  And dispatches a background processing task
  And returns a 202 Accepted response with the meeting ID and job status link within 2 seconds.

Scenario: File exceeds allowed parameters
  Given an authenticated user attempts to upload a file
  When the file size exceeds 2 GB or uses an unsupported MIME type (e.g., .exe)
  Then the upload is rejected immediately before object storage persistence
  And the system returns a 400 Bad Request error specifying the validation failure.
```

---

### US-002: Conversational Search with Source Grounding
**As an** Employee,  
**I want to** query the knowledge base in natural language,  
**So that** I can retrieve verifiable answers backed by exact meeting transcript timestamps.

#### Acceptance Criteria
```gherkin
Scenario: Relevant context found with accurate citation rendering
  Given the vector store contains indexed meeting transcripts accessible to the user
  When the user submits the query "What were the security concerns raised for the cloud migration?"
  Then the system filters vector search results by the user's role-based access permissions
  And retrieves the top-k relevant transcript chunks
  And generates a synthesis response grounded strictly in the retrieved context
  And includes inline citations formatted with `[Meeting Name - Timestamp]`.

Scenario: No relevant context found in index
  Given the query topics do not match any stored transcripts in the user's tenant space
  When the user submits a query about an unrecorded event
  Then the system responds with a fallback indicating insufficient information
  And does not generate ungrounded or hallucinated answers.
```

---

### US-003: Review and Edit Extracted Artifacts
**As a** Manager,  
**I want to** review and edit auto-extracted decisions and action items,  
**So that** I can verify commitments, correct inaccurate speaker assignments, and ensure accountability.

#### Acceptance Criteria
```gherkin
Scenario: Editing an extracted action item assignee and text
  Given a processed meeting with generated action items
  When a Manager updates an action item description and changes the assignee from "Speaker 1" to "John Doe"
  Then the system updates the action item database record
  And logs the modification event (user, timestamp, original value, new value) in the audit log
  And updates the meeting detail view to reflect the human-verified state.
```

---

## 3. End-to-End User Journey (Golden Path)

```
[1. User Login] ---> [2. Dashboard] ---> [3. Upload Media] ---> [4. Validation]
                                                                        |
[7. Verified Answer] <-- [6. Search & RAG] <-- [5. Processing & Indexing]
 (with Citations)           (Chat Interface)       (STT -> Diarization -> Extract)
```

1. **Authentication:** User logs in via secure credentials and receives a scoped session token.
2. **Dashboard Navigation:** User views recent organization meetings, processing status updates, and action item summaries.
3. **Media Upload:** User selects and uploads a recorded meeting file (`.mp4`, `.wav`, or `.mp3`) via the web client.
4. **Validation:** API gateway validates session token, file payload constraints, MIME type, and tenant storage quota.
5. **Asynchronous Pipeline Processing:**
   - **Ingestion:** File persisted in object storage; ingestion job enqueued in Redis/Celery.
   - **Transcription & Diarization:** Audio extracted, processed through Speech-to-Text (STT) for timestamped transcript generation, and run through speaker diarization.
   - **AI Extraction:** LLM pipeline extracts structured summary, key decisions, action items, risks, and deadlines.
   - **Indexing:** Transcript chunks are embedded using an embedding model and indexed into a vector database alongside metadata (tenant ID, meeting ID, speaker, timestamp).
6. **Search & RAG Chat:** User navigates to the Q&A interface and executes a natural language query against historical organizational meetings.
7. **Grounded Answer Delivery:** Search service filters context by user permissions, fetches top semantic chunks, and generates a response complete with clickable, timestamped transcript citations.

---

## 4. Functional Requirements

### A. Authentication & Session Management
- **FR-AUTH-01:** System shall support local username/password authentication using bcrypt hashing ($k=12$).
- **FR-AUTH-02:** System shall issue stateless JSON Web Tokens (JWT) upon successful login with a 15-minute access token lifespan and a 7-day sliding refresh token.
- **FR-AUTH-03:** System architecture shall be engineered for future enterprise Single Sign-On (SSO) integration via SAML 2.0 and OAuth2 / OIDC providers without database schema redesign.
- **FR-AUTH-04:** System shall enforce Role-Based Access Control (RBAC) across three primary roles: System Admin, Manager, and Standard Employee.

### B. Meeting Management
- **FR-MTG-01:** System shall support complete CRUD operations for meeting entities across web endpoints.
- **FR-MTG-02:** System shall validate uploaded media files, strictly enforcing supported formats (`.mp4`, `.wav`, `.mp3`) and a maximum file size limit of 2 GB per upload.
- **FR-MTG-03:** System shall track and display real-time meeting processing status using states: `PENDING`, `UPLOADING`, `TRANSCRIBING`, `DIARIZING`, `EXTRACTING`, `INDEXED`, and `FAILED`.
- **FR-MTG-04:** System shall provide detailed processing failure reason codes in administrative views for troubleshooting.

### C. Transcription
- **FR-TRN-01:** System shall extract 16kHz mono audio streams from uploaded video containers prior to Speech-to-Text processing.
- **FR-TRN-02:** System shall generate Word-Error-Rate (WER) optimized text transcripts complete with word-level and sentence-level start/end timestamps.
- **FR-TRN-03:** System shall persist normalized, time-indexed transcripts in relational storage associated with the meeting record.

### D. Speaker Intelligence
- **FR-SPK-01:** System shall execute speaker diarization to separate distinct voices into discrete speaker turns (`Speaker 0`, `Speaker 1`).
- **FR-SPK-02:** System shall map speaker turns directly to corresponding transcript text blocks with timestamp alignment.
- **FR-SPK-03:** System shall provide an interface allowing users with Manager or Admin roles to manually rename speaker labels (e.g., map `Speaker 0` to `John Doe`) across the entire transcript with a single confirmation.

### E. Meeting Intelligence
- **FR-INT-01:** System shall generate structured meeting artifacts using configured LLM pipelines within 120 seconds of transcription completion.
- **FR-INT-02:** System shall extract executive summaries structured in short narrative paragraphs and key bullet points.
- **FR-INT-03:** System shall extract explicit decisions made during the meeting, including who made or approved the decision where available.
- **FR-INT-04:** System shall extract action items, identifying the task description, suggested assignee, and explicit or implicit due date.
- **FR-INT-05:** System shall extract operational and project risks, blockers, and dependencies mentioned in the recording.

### F. Knowledge & Search
- **FR-SCH-01:** System shall segment time-indexed transcripts into overlapping semantic chunks (target size: 512 tokens; overlap: 64 tokens).
- **FR-SCH-02:** System shall generate dense vector embeddings for all transcript chunks using a standard enterprise embedding model.
- **FR-SCH-03:** System shall store vector embeddings in a vector database with attached metadata attributes: `tenant_id`, `meeting_id`, `speaker_id`, `start_time`, `end_time`.
- **FR-SCH-04:** System shall provide hybrid search capabilities combining dense vector semantic search with sparse keyword search (BM25).

### G. AI Assistant & RAG
- **FR-RAG-01:** System shall accept natural language queries and retrieve context using hybrid search over vector indices.
- **FR-RAG-02:** System shall strictly enforce permission-aware filtering during vector retrieval, ensuring users can only search meetings they are authorized to access.
- **FR-RAG-03:** System shall synthesize context into conversational answers, embedding explicit, timestamped citations pointing back to the precise transcript source (e.g., `[Q3 Planning - 14:23]`).
- **FR-RAG-04:** System shall enforce groundedness constraints, requiring the LLM to decline answering if the retrieved context lacks sufficient information.

---

## 5. Non-Functional Requirements (NFRs)

### Performance
- **NFR-PRF-01 (API Latency):** Core operational REST APIs (CRUD, meeting lists, user management) shall respond with $P_{95} < 500	ext{ ms}$ under standard load.
- **NFR-PRF-02 (RAG Latency):** End-to-end conversational RAG query execution (retrieval + LLM generation) shall return the full response within $P_{90} < 5.0	ext{ seconds}$ and $P_{99} < 10.0	ext{ seconds}$.
- **NFR-PRF-03 (Processing Throughput):** Async pipeline processing time for a 60-minute meeting file shall complete (transcription through vector indexing) within $\le 20\%	ext{ of total audio duration}$ (i.e., $\le 12	ext{ minutes}$).

### Scalability Targets
- **NFR-SCL-01 (Concurrency):** System shall support 100 concurrent active users executing API requests and search queries simultaneously without performance degradation.
- **NFR-SCL-02 (Ingestion Target):** System shall support an ingestion throughput capacity of up to 1,000 processed meetings per day across the tenant base.
- **NFR-SCL-03 (Storage Capacity):** Initial system deployment shall accommodate up to 10 TB of raw media and transcript object storage, with automated scaling policies.

### Availability & Reliability
- **NFR-AVL-01 (Uptime):** System API services shall maintain $99.9\%	ext{ operational uptime}$ calculated on a monthly basis, excluding scheduled maintenance windows.
- **NFR-REL-01 (Task Resilience):** Background task workers shall implement exponential backoff retry strategies (max 3 retries) for failed API calls to external ML services.
- **NFR-REL-02 (Dead-Letter Handling):** Tasks failing after maximum retries shall be routed to a Dead-Letter Queue (DLQ) with alert notifications sent to system administrators.
- **NFR-REL-03 (Idempotency):** Pipeline task execution must be fully idempotent; re-processing a meeting must overwrite stale data without leaving orphan vector embeddings or duplicate relational rows.

### AI Quality & Accuracy Metrics
- **NFR-AIQ-01 (Transcription Accuracy):** Speech-to-Text engine shall achieve a Word Error Rate ($	ext{WER}$) $\le 10\%$ on clear audio inputs (signal-to-noise ratio $> 20	ext{ dB}$).
- **NFR-AIQ-02 (Diarization Error Rate):** Speaker diarization pipeline shall maintain a Diarization Error Rate ($	ext{DER}$) $\le 12\%$ on meetings with $\le 6$ distinct participants.
- **NFR-AIQ-03 (Grounding & Hallucination Avoidance):** RAG synthesis pipeline shall achieve $\ge 95\%$ groundedness accuracy on benchmark evaluation datasets (zero unsupported factual claims).
- **NFR-AIQ-04 (Citation Precision):** Generated citations must point to the correct 30-second window containing the source context in $\ge 90\%$ of evaluated answers.

---

## 6. MVP Scope Boundary

```
+------------------------------------------------------------------------------------+
|                                  IN SCOPE (MVP)                                    |
+------------------------------------------------------------------------------------+
| - Media Upload: MP4, WAV, MP3 (Async batch processing)                             |
| - STT Transcription & Speaker Diarization                                          |
| - AI Extraction: Executive Summary, Decisions, Action Items, Risks                 |
| - Hybrid Search (BM25 + Dense Vector Embeddings)                                   |
| - Grounded RAG Chat with Timestamped Transcript Citations                          |
| - Authentication: Local Auth + JWT (SSO-ready interface)                           |
| - RBAC: Admin, Manager, Employee                                                   |
| - User, Organization, and Basic Audit Logging Interfaces                           |
+------------------------------------------------------------------------------------+

+------------------------------------------------------------------------------------+
|                             OUT OF SCOPE (Deferred)                                |
+------------------------------------------------------------------------------------+
| - Real-time Meeting Bots (Zoom / MS Teams / Google Meet live join bots)            |
| - Live Audio Streaming / Real-time In-Meeting Assistant                            |
| - External Integrations (Bidirectional Jira, Slack, Salesforce, Confluence sync)   |
| - Enterprise SAML 2.0 / OIDC Identity Federation                                   |
| - Native Mobile Applications (iOS / Android)                                       |
| - Multi-Region Database Replication & Cross-Region Active-Active Failover          |
| - Autonomous AI Background Agents                                                  |
+------------------------------------------------------------------------------------+
