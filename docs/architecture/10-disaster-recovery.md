# 10: Disaster Recovery

## 1. Business Continuity Targets
- **Recovery Point Objective (RPO):** 1 Hour (MVP tier).
- **Recovery Time Objective (RTO):** 4 Hours (MVP tier).

## 2. Backup Strategies
- **PostgreSQL:** WAL archiving to S3 using pgBackRest. Daily full snapshots.
- **Object Storage (MinIO):** Bucket replication to cold storage / remote region.
- **Redis:** Operates purely as an ephemeral task queue and cache. No persistent backup required; active tasks re-queued on crash.

## 3. Failure Scenarios & SOPs

### 3.1 Total Database Crash
- **Action:** Provision new DB instance. Restore latest full snapshot. Replay WAL up to failure point (Point-in-Time Recovery).

### 3.2 Celery Worker Node Crash
- **Action:** Redis `visibility_timeout` will expire. Unacknowledged tasks (e.g., transcription in progress) will be redelivered to a healthy worker automatically. Safe because tasks are idempotent.

### 3.3 External LLM Provider Outage
- **Action:** Circuit breaker trips after 3 consecutive 5xx errors. API returns 503 for extraction endpoints. Redis tasks enter exponential backoff and DLQ if outage exceeds 24 hours.
