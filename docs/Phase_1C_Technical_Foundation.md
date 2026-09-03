# Phase 1C: Technical Foundation

## 1. Domain Entities & Data Model

### Primary Domain Entities
* **Tenant:** `id`, `name`, `domain`, `status`, `created_at`, `updated_at`
* **User:** `id`, `tenant_id`, `email`, `password_hash`, `full_name`, `status`, `created_at`
* **Role:** `id`, `tenant_id`, `name` (Admin, Manager, Employee), `description`
* **Permission:** `id`, `code` (e.g., `meeting:read`, `meeting:write`), `description`
* **Meeting:** `id`, `tenant_id`, `title`, `description`, `scheduled_start`, `duration_seconds`, `status`, `created_by_user_id`
* **Recording:** `id`, `meeting_id`, `object_key`, `file_format`, `file_size_bytes`, `duration_seconds`, `checksum`
* **MeetingParticipant:** `id`, `meeting_id`, `user_id` (optional), `external_email`, `display_name`, `role`
* **Transcript:** `id`, `meeting_id`, `language`, `word_count`, `version`, `created_at`
* **TranscriptSegment:** `id`, `transcript_id`, `speaker_id`, `start_time_ms`, `end_time_ms`, `text`, `confidence`
* **Speaker:** `id`, `meeting_id`, `label` (e.g., `SPEAKER_00`), `confidence`
* **SpeakerMapping:** `id`, `speaker_id`, `mapped_user_id`, `verified_by_user_id`, `updated_at`
* **Summary:** `id`, `meeting_id`, `executive_summary`, `key_points` (JSONB), `model_version`
* **Topic:** `id`, `meeting_id`, `name`, `description`, `start_time_ms`, `end_time_ms`
* **Decision:** `id`, `meeting_id`, `description`, `decision_maker_speaker_id`, `timestamp_ms`
* **ActionItem:** `id`, `meeting_id`, `description`, `assignee_user_id`, `due_date`, `status` (OPEN, COMPLETED)
* **Risk:** `id`, `meeting_id`, `description`, `severity` (LOW, MEDIUM, HIGH), `mitigation`
* **Document:** `id`, `tenant_id`, `title`, `source_type` (MEETING_TRANSCRIPT, DOC), `source_id`, `created_at`
* **Chunk:** `id`, `document_id`, `chunk_index`, `content`, `token_count`, `metadata` (JSONB: start_time, end_time, speaker_id)
* **Embedding:** `id`, `chunk_id`, `vector` (vector(1536)), `model_name`
* **Conversation:** `id`, `tenant_id`, `user_id`, `title`, `created_at`
* **Message:** `id`, `conversation_id`, `sender_type` (USER, ASSISTANT), `content`, `created_at`
* **Citation:** `id`, `message_id`, `chunk_id`, `meeting_id`, `timestamp_start_ms`, `timestamp_end_ms`, `relevance_score`
* **ProcessingJob:** `id`, `meeting_id`, `job_type`, `status`, `retry_count`, `error_message`, `checkpoint_data` (JSONB)
* **AuditLog:** `id`, `tenant_id`, `user_id`, `action`, `resource_type`, `resource_id`, `ip_address`, `timestamp`

### Core Relational Hierarchy
```
+---------------------------------------------------------------------------------+
|                                     TENANT                                      |
+---------------------------------------------------------------------------------+
          |                                  |                              |
          v                                  v                              v
   +--------------+                   +--------------+              +---------------+
   |    USERS     |                   |   MEETINGS   |              |   DOCUMENTS   |
   +--------------+                   +--------------+              +---------------+
          |                                  |                              |
          +---> Roles/Permissions            +---> Recordings               +---> Chunks
                                             +---> Participants                    |
                                             +---> Transcripts                     v
                                             |       +---> Segments           Embeddings
                                             |       +---> Speakers
                                             |               +---> Mappings
                                             +---> Artifacts
                                             |       +---> Summaries
                                             |       +---> Decisions
                                             |       +---> ActionItems
                                             |       +---> Risks
                                             +---> ProcessingJobs
```

---

## 2. Processing State Machine

```
               +-------------------------------------------------------------------------------+
               |                                                                               |
               v                                                                               |
          [ UPLOADED ] ---> [ VALIDATING ] ---> [ AUDIO_EXTRACTING ] ---> [ TRANSCRIBING ]     |
                                    |                     |                      |             |
                                    v                     v                      v             |
                              [ FAILED ]            [ FAILED ]             [ FAILED ]          |
                                    |                     |                      |             |
                                    +---------------------+----------------------+             |
                                                          |                                    |
                                                          v                                    |
                                                     [ RETRY ] --------------------------------+
                                                          | (Max Retries Exceeded)
                                                          v
                                                   [ DEAD_LETTER ]

   [ TRANSCRIBING ] ---> [ DIARIZING ] ---> [ ANALYZING ] ---> [ INDEXING ] ---> [ COMPLETED ]
            |                  |                  |                 |
            v                  v                  v                 v
        [ FAILED ]         [ FAILED ]         [ FAILED ]        [ FAILED ]
```

### State Transitions & Lifecycle Rules
* **UPLOADED:** File successfully stored in object storage. `ProcessingJob` initialized.
* **VALIDATING:** Check file integrity, MIME type, payload constraints, and tenant quotas.
* **AUDIO_EXTRACTING:** Extract 16kHz mono WAV stream from container formats via FFmpeg.
* **TRANSCRIBING:** Speech-to-Text inference generating time-stamped text segments.
* **DIARIZING:** Speaker identification and segment-speaker alignment.
* **ANALYZING:** LLM structured extraction (Summaries, Decisions, Action Items, Risks).
* **INDEXING:** Text chunking, embedding generation, and vector insertion into `pgvector`.
* **COMPLETED:** All artifacts persisted, vector index updated, meeting status set to `READY`.

### Error Handling & Reliability Strategy
* **Failure State (`ANY_STATE` → `FAILED`):** Catches uncaught exceptions or service timeouts. Job state and exception trace stored in `ProcessingJob.checkpoint_data`.
* **Retry Strategy (`FAILED` → `RETRY`):** Celery workers retry failed tasks using exponential backoff ($2^n 	imes 	ext{base_delay}$, max 3 retries). Retries resume from the last successful checkpoint stage.
* **Dead-Letter Queue (`RETRY` → `DEAD_LETTER`):** If max retries are exhausted, the job is routed to a Dead-Letter Queue (DLQ). The meeting status is set to `FAILED`, alerting administrators via system observability metrics.

---

## 3. End-to-End AI & Retrieval Pipeline

```
+------------------+     +------------------+     +-------------------+     +--------------------+
| Recording File   | --> | FFmpeg Extraction| --> | Audio Normalizer  | --> | Speech-to-Text     |
| (MP4 / WAV)      |     | (16kHz Mono WAV) |     | (EBU R128 / Gain) |     | (faster-whisper)   |
+------------------+     +------------------+     +-------------------+     +--------------------+
                                                                                  |
                                                                                  v
+------------------+     +------------------+     +-------------------+     +--------------------+
| Canonical        | <-- | Transcript       | <-- | Speaker           | <-- | Speaker            |
| Transcript       |     | Alignment        |     | Mapping           |     | Diarization        |
+------------------+     +------------------+     +-------------------+     +--------------------+
       |
       v
+------------------+     +------------------+     +-------------------+     +--------------------+
| Structured LLM   | --> | Text Chunking    | --> | Embedding         | --> | pgvector Storage   |
| Extraction       |     | (512 tokens /    |     | Generation        |     | (HNSW Index +      |
| (JSON Schema)    |     |  64 overlap)     |     | (Text Embedding)  |     |  Metadata)         |
+------------------+     +------------------+     +-------------------+     +--------------------+

========================================= RETRIEVAL PIPELINE =========================================

+------------------+     +------------------+     +-------------------+     +--------------------+
| User Query       | --> | RBAC Metadata    | --> | Hybrid Retrieval  | --> | Reranking Model    |
| (RAG Chat)       |     | Filtering        |     | (Dense + Sparse   |     | (Cross-Encoder)    |
|                  |     | (Tenant / Role)  |     |  BM25)            |     |                    |
+------------------+     +------------------+     +-------------------+     +--------------------+
                                                                                  |
                                                                                  v
                                                  +-------------------+     +--------------------+
                                                  | Grounded LLM Response   | Grounded LLM       |
                                                  | with Timestamp    | <-- | Generation         |
                                                  | Citations         |     | (LiteLLM Gateway)  |
                                                  +-------------------+     +--------------------+
```

---

## 4. Architecture Boundaries & Service Topology

```
+-------------------------------------------------------------------------------------------------+
|                                    FRONTEND LAYER (Next.js)                                     |
|                          TypeScript | Tailwind CSS | React Query                                |
+-------------------------------------------------------------------------------------------------+
                                                  | HTTPS / REST / WebSockets
                                                  v
+-------------------------------------------------------------------------------------------------+
|                                    CORE API LAYER (FastAPI)                                     |
|  +--------------+  +--------------+  +---------------+  +--------------+  +------------------+  |
|  | Auth Router  |  | Mtg Router   |  | Search Router |  | Chat Router  |  | Admin Router     |  |
|  +--------------+  +--------------+  +---------------+  +--------------+  +------------------+  |
+-------------------------------------------------------------------------------------------------+
            |                                     |                                   |
            | Database Access                     | Enqueue Tasks                     | Object Storage
            v                                     v                                   v
+-----------------------+               +-------------------+               +---------------------+
| PERSISTENCE LAYER     |               | TASK QUEUE / CACHE|               | OBJECT STORAGE      |
| PostgreSQL + pgvector |               | Redis             |               | MinIO (S3 API)      |
+-----------------------+               +-------------------+               +---------------------+
                                                  |
                                                  v
+-------------------------------------------------------------------------------------------------+
|                                ASYNCHRONOUS WORKERS (Celery)                                    |
|  +------------------------+    +-----------------------+    +--------------------------------+  |
|  | Media Worker           |    | AI Worker             |    | Indexing Worker                |  |
|  | (FFmpeg / STT / Diar.) |    | (LLM Extraction)      |    | (Chunking / Embedding / Vector)|  |
|  +------------------------+    +-----------------------+    +--------------------------------+  |
+-------------------------------------------------------------------------------------------------+
```

---

## 5. Technology Stack Decisions

| Component | Selected Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.11+) | High performance (ASGI), native async support, strict data validation via Pydantic v2, and direct integration with Python ML ecosystems. |
| **Relational & Vector Store** | PostgreSQL 16 + pgvector | Eliminates the operational complexity of running a standalone vector DB. Supports ACID transactions, relational integrity, and vector similarity search (HNSW index) in a single database. |
| **Task Queue & Cache** | Redis 7 + Celery | Enterprise-standard distributed task execution engine. Redis acts as a low-latency broker, result backend, and caching layer for session and rate-limit data. |
| **Object Storage** | MinIO | S3-compatible, high-performance object storage for raw audio/video files. Enables straightforward cloud migration to AWS S3 or Google Cloud Storage without code refactoring. |
| **Media Processing** | FFmpeg | Industry-standard C library for audio stream extraction, channel downmixing (to 16kHz mono), and format normalization. |
| **ASR & Diarization Engine** | faster-whisper & pyannote.audio | `faster-whisper` provides CTranslate2-based Whisper inference yielding up to 4x speedup with lower memory overhead. `pyannote.audio` delivers state-of-the-art speaker diarization. |
| **LLM Gateway** | LiteLLM Gateway | Unified multi-provider abstraction layer (OpenAI, Azure, Bedrock, Self-hosted) providing standardized fallback handling, load balancing, budget tracking, and token usage metrics. |
| **Frontend Framework** | Next.js 14+ (React, TS) | Server-Side Rendering (SSR) for initial loads, strong TypeScript type safety, static optimization, and efficient client-side state management for rich interactive dashboards. |
| **Containerization** | Docker & Docker Compose | Containerized service packaging ensuring deployment parity across local development, staging, and production environments. |

---

## 6. Data Classification & Security Architecture

### Enterprise Data Tiers

| Classification Level | Target Assets | Access Scope | Encryption Policy | Audit Requirements |
| :--- | :--- | :--- | :--- | :--- |
| **Public** | System documentation, public product guides. | Unrestricted public access. | In-transit: TLS 1.3 | Standard HTTP access logging. |
| **Internal** | System telemetry, operational metrics, anonymized logs. | Authenticated employees. | In-transit: TLS 1.3 | Internal access logs. |
| **Confidential** | User profile metadata, non-sensitive meeting titles, organization schemas. | Tenant-bound authenticated users (RBAC). | In-transit: TLS 1.3<br>At-rest: AES-256 | Standard access and mutation logging. |
| **Restricted** | Raw audio/video files, transcripts, extracted summaries, decisions, action items, vector embeddings. | Strict tenant + meeting-level authorization checks. | In-transit: TLS 1.3<br>At-rest: AES-256 (KMS managed) | Comprehensive audit log (who accessed what, when, query parameters). |

### Security Mechanisms

#### 1. Tenant & User Isolation
* Multi-tenancy is enforced at the database level using `tenant_id` column partitioning and explicit application-level tenant context injection.
* Database operations utilize scoped sessions ensuring queries implicitly append `WHERE tenant_id = :current_tenant_id`.

#### 2. Vector Search Authorization Filters
Vector similarity queries strictly enforce permission boundaries prior to distance calculations using hybrid metadata filters:

```sql
SELECT c.id, c.content, c.metadata
FROM chunk c
JOIN embedding e ON e.chunk_id = c.id
JOIN meeting m ON c.metadata->>'meeting_id' = m.id::text
WHERE m.tenant_id = :current_tenant_id
  AND (
       m.created_by_user_id = :current_user_id 
       OR EXISTS (
           SELECT 1 FROM meeting_participant mp 
           WHERE mp.meeting_id = m.id AND mp.user_id = :current_user_id
       )
  )
ORDER BY e.vector <=> :query_embedding
LIMIT :top_k;
```

#### 3. Cryptographic Controls
* **In-Transit:** TLS 1.3 enforced across all external client-to-API communication and internal service-to-service communication.
* **At-Rest:** Object storage (MinIO) and relational database storage (PostgreSQL) encrypted using AES-256 with key rotation managed via an enterprise Key Management Service (KMS).

#### 4. Audit Logging & Data Retention
* **Audit Trail:** All read, create, update, and delete actions on `Restricted` assets trigger immutable log writes to `AuditLog` records containing `user_id`, `tenant_id`, `action`, `resource_id`, `timestamp`, and client `ip_address`.
* **Retention Schedule:** Raw audio/video files are automatically purged from object storage after a configurable tenant period (default: 90 days). Text transcripts, extracted structured metadata, and vector embeddings are retained until explicit user or tenant deletion.