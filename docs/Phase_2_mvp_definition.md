# Phase 2: MVP Definition & Scope Baseline

## 1. MVP Objective
The MVP enables multi-tenant enterprise teams to securely ingest asynchronous meeting media artifacts (audio/video), execute speaker-aware transcription and diarization, extract structured organizational artifacts (summaries, decisions, action items, risks), and perform permission-bound hybrid search and retrieval-augmented generation (RAG) with verifiable, timestamp-linked source citations.

---

## 2. Target Users & Access Boundaries

### Primary Personas
1. **Authenticated Knowledge Worker / Employee:** Ingests media artifacts, accesses workspace meeting archives, reviews transcripts, executes natural language queries against authorized meeting intelligence, and verifies claims via direct timestamp navigation.
2. **Workspace Admin:** Provisioning/deprovisioning users, managing workspace configuration, monitoring processing queue telemetry, and defining meeting visibility rules across organizational departments.

### Multi-Tenant & RBAC Isolation Boundaries
* **Tenant Isolation:** Hard separation at the data layer using logical database partitioning via `tenant_id` on all schema tables. Cross-tenant data leaks are prevented via global query scope filters enforced at the ORM layer and explicit tenant-scoped S3 bucket/prefix isolation.
* **Role-Based Access Control (RBAC):**
  * `ADMIN`: Full access to tenant configuration, user management, meeting archives, system telemetry, and audit logs.
  * `MEMBER`: Access restricted to meetings where the user is an explicit owner, designated attendee, or member of a designated access group (e.g., `department_id`).
  * `GUEST`: Access strictly bounded to explicitly shared individual meeting artifacts; restricted from global search vector querying.

---

## 3. The Golden User Journey (Vertical Slice)

1. **Authentication & Session Initialization:** User authenticates via JWT-based OAuth2 workflow; API issues scoped access tokens embedding `tenant_id`, `user_id`, and `role`.
2. **File Ingress & Client Validation:** User uploads media (`.mp4`, `.wav`, `.mp3`) through frontend client. Browser executes magic-byte validation and payload size checks (< 500 MB) before issuing multipart POST request.
3. **Persistent Storage & Job Queuing:** API stores raw file payload in object storage (`minio/s3`) under `s3://{tenant_id}/meetings/{meeting_id}/raw.*`, creates database record with state `UPLOADED`, and enqueues task payload onto Redis broker.
4. **Audio Normalization & Extraction:** Celery worker retrieves task, invokes FFmpeg wrapper to convert source media to standard target format: 16kHz, single-channel (mono), 16-bit PCM `.wav`.
5. **Speech-to-Text Transcription:** Worker passes normalized audio to `faster-whisper` (large-v3 model) using batched inference to produce raw word-level transcripts with exact start/end time offsets (`ms`).
6. **Speaker Diarization & Labeling:** `pyannote.audio` pipeline processes normalized audio to isolate distinct speaker embeddings, executing spectral clustering to generate speaker turns mapped to time intervals.
7. **Transcript Alignment & Intelligence Extraction:** Diarization turns are aligned with word timestamps to produce a structured, speaker-attributed transcript. The transcript is routed to an LLM via structured JSON schema prompting to extract summary, key decisions, action items (with assignees), and risks.
8. **Chunking, Embedding Generation & Vector Indexing:** Structured transcript is split into overlapping semantic chunks (512 tokens, 64-token overlap). Each chunk is embedded via a text embedding model (1536 dimensions) and written to PostgreSQL `transcript_chunks` with `tenant_id` and metadata filters.
9. **Hybrid Search Execution:** Knowledge worker submits natural language query. System generates query embedding, executing reciprocal rank fusion (RRF) combining full-text lexical search (`tsvector`) and dense vector distance search (`hnsw` cosine) filtered by user RBAC permissions.
10. **Context Assembly & Grounded RAG Generation:** Top-$K$ retrieved chunks are injected into a strict system prompt instruction enforcing zero-hallucination guardrails and mandatory timestamp referencing. Generation LLM constructs answer payload.
11. **Interactive UI Playback & Timestamp-Linked Citation Verification:** Client renders markdown response containing hyperlinked inline citations `[HH:MM:SS]`. Clicking a citation auto-seeks the integrated media player to the exact time offset in the transcript viewer.

---

## 4. MVP Feature Scope & P0/P1 Matrix

| Module | Capability | Priority | Technical Mechanism | Failure Mode / Fallback |
| :--- | :--- | :--- | :--- | :--- |
| **Auth & Access Control** | Tenant-isolated JWT auth & strict row-level access control | **P0** | FastAPI OAuth2 Bearer + SQLAlchemy session interceptors evaluating `tenant_id` & `user_id`. | Reject request with HTTP 401/403; emit security audit event log. |
| **Media Ingestion & Validation** | Asynchronous batch upload for MP4, WAV, MP3 formats | **P0** | Streaming upload to MinIO/S3 with magic-byte signature validation and file size limits (500 MB). | Client-side pre-flight validation error; immediate HTTP 400 rejection on invalid header/type. |
| **Processing Pipeline** | Asynchronous task execution & pipeline orchestration | **P0** | Celery task queues over Redis broker; FFmpeg media standardizer (16kHz mono PCM). | Set meeting status to `FAILED`; trigger exponential backoff retry (max 3 attempts). |
| **Speech-to-Text** | High-accuracy batched transcription | **P0** | `faster-whisper` runtime using `large-v3` weights with VAD (Voice Activity Detection) filtering. | Fallback to `medium.en` model configuration if GPU memory limits hit. |
| **Speaker Diarization** | Multi-speaker segmentation & transcript alignment | **P0** | `pyannote.audio` pipeline aligned via interval intersection algorithm against word timestamps. | Mark speakers as `SPEAKER_UNKNOWN` if cluster confidence falls below 0.45. |
| **Intelligence Extraction** | Structured extraction (Summary, Decisions, Action Items, Risks) | **P0** | Instructor / Pydantic JSON schema forcing structured LLM response output. | Retry generation with higher temperature (0.2); fallback to raw transcript rendering on structural parse failure. |
| **Knowledge Ingestion & Search** | Hybrid vector/lexical retrieval | **P0** | PostgreSQL `pgvector` with HNSW index (cosine) fused with `tsvector` keyword search using RRF. | Fallback to full-text lexical search if vector distance calculation fails or times out (> 1s). |
| **Grounded RAG Chat** | Q&A with verifiable timestamp citations | **P0** | Context-injected LLM generation restricted strictly to retrieved context blocks with exact time offsets. | Output "Insufficient context to answer query" if retrieval similarity scores fall below threshold (< 0.65). |
| **Speaker Re-labeling** | Manual UI override for speaker names | **P1** | REST API endpoint updating `speaker_label` across all transcript chunks for a specific `meeting_id`. | Dynamic UI-only optimistic state rollback if persistent update fails. |
| **Notifications** | Async status update delivery to frontend | **P1** | Polling API endpoint (`/api/v1/meetings/{id}/status`) backed by Redis key state transitions. | Graceful UI polling degradation (backoff interval expansion from 2s to 15s). |

---

## 5. Scope Boundaries: In-Scope vs. Explicitly Out-of-Scope

| In-Scope (MVP Guarantees) | Explicitly Out-of-Scope (Deferred) | Technical Rationale for Omission |
| :--- | :--- | :--- |
| **Batch Media Upload:** Async upload of pre-recorded `.mp4`, `.wav`, `.mp3` files via web interface. | **Live Meeting Bots:** Autonomous bot joiners for Zoom, Teams, or Google Meet. | Avoids real-time WebRTC/SIP network volatility, complex bot-evasion handling, and real-time audio chunk processing complexity. |
| **S3-Compatible Object Storage:** Storing raw audio/video and extracted artifacts in MinIO/S3. | **Real-Time Streaming Transcription:** Streaming WebSocket STT during live calls. | Eliminates low-latency streaming infrastructure requirements; optimizes for high-accuracy batch processing instead. |
| **Celery Asynchronous Pipeline:** Queue-driven processing pipeline (FFmpeg, Whisper, Pyannote). | **Third-Party SaaS Integrations:** Bidirectional syncing with Jira, Slack, Salesforce, Confluence. | Prevents API integration drift, complex oauth token refresh loops, and external rate-limiting bottlenecks during core MVP validation. |
| **Structured Intelligence Schemas:** Strict JSON extraction of summaries, action items, decisions, and risks. | **Calendar Synchronization:** Automated meeting recording via Google Calendar / Outlook APIs. | Removes background OAuth calendar scanning complexity and tenant authorization friction. |
| **Hybrid Search & Vector Retrieval:** Combined `pgvector` + PostgreSQL text search with HNSW indexing. | **Mobile Applications:** Native iOS or Android client applications. | Desktop web client provides complete surface area required to validate enterprise knowledge workflows. |
| **RBAC-Filtered RAG:** Tenant and user isolation strictly enforced on search and generation context. | **Multi-Region Distributed Clustering:** Multi-region active-active database and worker deployment. | Single-region high-availability cluster drastically reduces deployment overhead while meeting MVP reliability SLAs. |
| **Verifiable Timestamp Navigation:** Citations linked directly to exact audio player time offsets. | **Autonomous Multi-Agent Loops:** Unbounded multi-agent reasoning frameworks (e.g., AutoGen, CrewAI). | Prevents non-deterministic execution paths, excessive token usage overhead, and runaway latency. |

---

## 6. End-to-End MVP Data Flow

### Architecture Data-Flow Diagram

```text
+------------------+
| Client / Frontend|
+--------+---------+
         | 1. Upload Media (.mp4/.wav)
         v
+--------+---------+      2. Write Raw File     +----------------+
|    FastAPI API   |--------------------------->| MinIO / S3     |
|    Application   |                            | Object Storage |
+--------+---------+                            +----------------+
         |
         | 3. Enqueue Job Task
         v
+--------+---------+
|   Redis Broker   |
+--------+---------+
         |
         | 4. Fetch Job Payload
         v
+--------+---------+     5. Process Audio       +------------------+
|   Celery Worker  |--------------------------->| FFmpeg           |
|   Processing     |<---------------------------| (16kHz Mono WAV) |
|   Engine         |                            +------------------+
|                  |     6. Transcribe & Diarize+------------------+
|                  |--------------------------->| faster-whisper & |
|                  |<---------------------------| pyannote.audio   |
|                  |                            +------------------+
|                  |     7. Extract Intelligence+------------------+
|                  |--------------------------->| Generation LLM   |
|                  |<---------------------------| (Structured JSON)|
|                  |                            +------------------+
|                  |     8. Chunk & Embed       +------------------+
|                  |--------------------------->| Embedding Model  |
|                  |<---------------------------| (1536-dim vector)|
|                  |                            +------------------+
|                  |     9. Write Relational & Vector Data
|                  +-----------------------------------+
|                                                      |
v                                                      v
+------------------------------------------------------+-----------+
| PostgreSQL 16 (Relational Schema + pgvector HNSW Index)          |
+------------------------------------------------------+-----------+
                                                       ^
                                                       | 10. RBAC Hybrid Search
                                                       |     (Vector + Lexical)
                                              +--------+----------+
                                              | RAG Query Engine  |
                                              +--------+----------+
                                                       |
                                                       | 11. Grounded Context
                                                       v
                                              +-------------------+
                                              | Generation LLM    |
                                              +--------+----------+
                                                       |
                                                       | 12. Response + Citations
                                                       v
                                              +-------------------+
                                              | Client / Frontend |
                                              +-------------------+
```

### Pipeline State Machine Transitions

```text
[UPLOADED] ──> [VALIDATING] ──> [AUDIO_EXTRACTING] ──> [TRANSCRIBING]
                                                               │
[COMPLETED] <── [INDEXING] <── [ANALYZING] <── [DIARIZING] <───┘
     │
     └──> (On Failure at any step) ──> [FAILED] ──> (Retry Count < 3) ──> [RETRY_QUEUED] ──> [PREVIOUS_STATE]
                                          │
                                          └──> (Retry Count >= 3) ──> [FATAL_FAILED]
```

---

## 7. MVP Success Criteria & Evaluation Framework

### 1. Functional Success Metrics
* **100% Pipeline Completion Rate:** Execution from media upload through vector indexing completes without human intervention for valid media payloads (< 500 MB, supported formats).
* **Zero Cross-Tenant Leakage:** 100% boundary isolation verified via automated integration tests attempting unauthorized cross-tenant vector retrieval and meeting access.

### 2. System Performance Targets
* **API Latency:** Metadata, meeting lists, and transcript detail queries respond in $< 500	ext{ ms}$ at $p95$.
* **Batch Processing Processing Speed (Real-Time Factor - RTF):** Pipeline processing turnaround time ratio $< 0.5	imes$ meeting duration (e.g., a 60-minute meeting must process fully in $< 30	ext{ minutes}$).
* **Vector Search Retrieval Latency:** Hybrid retrieval query execution latency $< 250	ext{ ms}$ at $p95$ across a corpus of $100,000$ vector chunks.

### 3. AI Quality & Evaluation Strategy
* **Word Error Rate (WER):** Target baseline $\le 12\%$ WER on standard business English audio (clear mic, low background noise).
* **Diarization Error Rate (DER):** Target baseline $\le 15\%$ DER for meetings with up to 6 distinct speakers.
* **Information Extraction Precision/Recall:** Structured extraction (action items, decisions) evaluated against human-annotated reference benchmarks targeting $\ge 85\%$ F1-score.
* **RAG Faithfulness & Groundedness:** Evaluated via Ragas/TruLens frameworks targeting a Faithfulness Score $\ge 0.90$. Zero-tolerance policy for ungrounded citations (100% of generated claims must map to a valid source chunk).

---

## 8. Acceptance Criteria (Gherkin Scenarios)

### Scenario 1: Successful Media Upload, Validation, and Job Scheduling
```gherkin
Given an authenticated user with "MEMBER" role in Tenant "AcmeCorp"
When the user uploads a valid media file "quarterly_sync.mp4" with size "150MB"
Then the API should validate the magic bytes and accept the payload with HTTP 202 Accepted
And store the file in object storage at "s3://acmecorp/meetings/{meeting_id}/raw.mp4"
And create a database record with state "UPLOADED"
And push a task payload containing "meeting_id" to the Redis broker queue.
```

### Scenario 2: Asynchronous Pipeline Completion & Artifact Generation
```gherkin
Given a meeting record in state "UPLOADED" queued on the processing broker
When the worker processes the file through media normalization, STT, diarization, and LLM analysis
Then the meeting status transition state should sequence sequentially through "AUDIO_EXTRACTING", "TRANSCRIBING", "DIARIZING", "ANALYZING", and "INDEXING"
And populate the "transcript_chunks" table with generated embeddings of vector dimension 1536
And create structured extraction records for "summary", "decisions", "action_items", and "risks"
And set the final meeting status to "COMPLETED".
```

### Scenario 3: Grounded Retrieval and Timestamp Navigation
```gherkin
Given a processed meeting "quarterly_sync" in state "COMPLETED" belonging to Tenant "AcmeCorp"
And an authenticated user belonging to Tenant "AcmeCorp"
When the user submits the query "What were the decisions regarding Q3 budget allocation?"
Then the RAG engine should return a markdown response grounded exclusively in the meeting context
And include inline clickable citations containing accurate timestamp markers matching the transcript (e.g., "[00:14:22]")
And clicking the citation link must update the frontend media player current time state to "862" seconds.
```

---

## 9. Known MVP Limitations & Technical Debt

1. **Cold-Start Latency for Local Inference Models:** Initial worker initialization experiences a $15	ext{s}$–$30	ext{s}$ latency penalty due to heavy weight loading (`faster-whisper`, `pyannote.audio`) into memory/GPU cache.
2. **Backpressure Under Burst Loads:** The worker queue uses fixed concurrency. Rapid concurrent uploads exceeding available worker threads will lead to processing delays, as autoscale worker policies are deferred post-MVP.
3. **Context Window Clipping on Multi-Hour Transcripts:** Meetings exceeding 3 hours ($> 30,000$ words) may exceed single-pass context window limits during intelligence extraction, requiring chunked map-reduce summarization strategies.
4. **Coarse-Grained Speaker Alignment Overhead:** Overlapping speaker speech segments (simultaneous cross-talk) are currently simplified to the primary dominant speaker, leading to minor diarization precision drop-offs in heated discussions.

---

## 10. Definition of Done (DoD)

To certify Phase 2 as complete and ready for production staging deployment, the build artifact must fulfill the following mandatory checklist:

- [ ] **Core Service Contracts Implemented:** All defined API routes (`/auth`, `/meetings`, `/chat`, `/admin`) fully functional and compliant with Phase 1 OpenAPI specifications.
- [ ] **Database & Migrations Standardized:** Alembic migration scripts fully tested up and down; baseline SQL initializers executed successfully on PostgreSQL 16 with `pgvector` enabled.
- [ ] **Automated Test Coverage Met:**
  - Unit test coverage $\ge 80\%$ across core service modules.
  - Integration tests verifying tenant boundary enforcement and RBAC restrictions.
  - End-to-end automated test successfully executing the full Golden User Journey.
- [ ] **Observability & Telemetry Integrated:**
  - Structured JSON logging implemented across API and Celery workers with correlation IDs (`trace_id`).
  - Worker healthcheck endpoints returning operational metrics to Docker runtime.
- [ ] **Architectural & Security Compliance:**
  - Zero hardcoded credentials or unencrypted secrets present in code repository.
  - All media access points protected behind ephemeral pre-signed URL signatures or authenticated gateway proxies.