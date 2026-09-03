# 00: Architecture Principles

## 1. Core Principles

### 1.1 Security & Tenant Isolation by Design
Security is intrinsically woven into the data model and access patterns. Zero cross-tenant leakage is guaranteed via enforced Row-Level Security (RLS) in PostgreSQL, partitioned object storage paths (`s3://tenant-{id}/`), and deterministic tenant-id filtering in all vector similarity searches.

### 1.2 Asynchronous Batch Processing
The core API must remain highly available and responsive. All CPU/GPU-intensive operations (media encoding, ASR, Diarization, LLM inference, indexing) are strictly decoupled using a message broker (Redis) and processed by isolated Celery worker pools. API routes acknowledge ingestion immediately (HTTP 202) and return a job correlation ID.

### 1.3 Canonical Transcript as Single Source of Truth
The `Raw Media` yields a `Canonical Transcript` (time-aligned text per speaker). All downstream AI artifacts (summaries, action items, vector embeddings) are derived *only* from this canonical transcript. Vector chunks are indexed representations, not the system of record.

### 1.4 Deterministic Authorization Before RAG Context
The LLM is explicitly untrusted for access control. Authorization is evaluated deterministically at the API layer (RBAC) and database layer (RLS). Vector retrieval pre-filters chunks by `tenant_id` and `meeting_id` prior to executing similarity search. Context assembled for the LLM contains only authorized data.

### 1.5 Idempotent and Resilient Workflows
All state mutations and worker tasks are idempotent. Workflows utilize explicit state machines (`PENDING` -> `PROCESSING` -> `COMPLETED` | `FAILED`), checkpointing, Celery retry policies with exponential backoff, and Dead-Letter Queues (DLQ) for manual intervention.

## 2. Architectural Style
Modular Monolith for the Core API (FastAPI) to reduce deployment complexity in the MVP phase, coupled with horizontally scalable, specialized async workers for Media/AI pipelines.

## 3. System & MVP Boundaries
**In Scope for MVP:**
- Internal platform orchestration.
- Async media processing and AI metadata generation.
- Proprietary Next.js Web Client.

**Out of Scope for MVP:**
- Live meeting bot recording (Zoom/Teams integrations deferred).
- Direct push to third-party CRMs (Salesforce/HubSpot deferred).
- Real-time streaming transcription.
