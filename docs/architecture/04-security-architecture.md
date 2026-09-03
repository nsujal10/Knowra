# 04: Security Architecture

## 1. Multi-Tenancy Isolation
- **Database Layer:** Hard enforced Row-Level Security (RLS) injected per-request via API middleware setting session variables (`app.current_tenant`).
- **Storage Layer:** Object paths strict scoped to `tenant_id/meeting_id/file`.
- **Vector Layer:** `tenant_id` is a mandatory hard filter in the `WHERE` clause before `ORDER BY embedding <=> query`.

## 2. Authentication
- **Mechanism:** JWT (JSON Web Tokens).
- **Tokens:** Short-lived Access Token (15 mins) via HTTP headers, long-lived Refresh Token (7 days) via HTTP-Only, Secure cookies.

## 3. Role-Based Access Control (RBAC)
- **Employee:** Can upload/view own meetings.
- **Manager:** Can view meetings of direct reports.
- **Executive:** Can query cross-organizational aggregated intelligence.
- **Admin:** IT settings, user provisioning.
- **Knowledge_Admin:** Taxonomy and custom extraction prompt tuning.

## 4. Encryption
- **In-Transit:** TLS 1.3 enforced on all API endpoints and internal inter-service communication.
- **At-Rest:** PostgreSQL Volume Encryption (KMS), MinIO AES-256 server-side encryption (SSE-S3).

## 5. Deterministic RAG Boundary
The LLM is explicitly bypassable if context is manipulated. Therefore, access control happens *before* RAG. The system fetches only vector chunks the user is authorized to read (via RLS and explicit query bounds).

## 6. Audit Logging
Every mutation and data access logs to `audit_logs` table:
- `id`, `timestamp`, `actor_user_id`, `tenant_id`, `action` (e.g., `MEETING_VIEW`, `SEARCH_QUERY`), `target_entity_id`, `ip_address`.
