# 08: Data Flow Diagrams

## Level 0: Context Diagram
```text
[User/Admin] <---(HTTPS)---> [Enterprise Meeting Platform]
                                    |         |
                              (API Calls)  (Object Storage)
                                    v         v
                              [LLM Provider][S3 / MinIO]
```

## Level 1: System DFD
1. **Upload:** User -> Core API -> MinIO (Media) & DB (Metadata).
2. **Dispatch:** Core API -> Redis (Task).
3. **Processing:** Redis -> Worker -> DB (Update Status).
4. **Retrieval:** User -> Core API -> DB (RBAC check + Data) -> User.

## Level 2: Media & AI Processing DFD
```text
(MinIO) -> Raw Media (MP4/WAV)
  |
  v
[FFmpeg Worker] ---> Normalized Audio (16kHz Mono FLAC) ---> (MinIO)
  |
  +---> [faster-whisper] ---> Raw Words & Timestamps (JSON)
  |
  +---> [pyannote.audio] ---> Speaker Segments & Timestamps (JSON)
  |
  v
[Alignment Engine] ---> Canonical Transcript Segments ---> (PostgreSQL)
  |
  v
[LLM Extraction] ---> Summaries, Actions, Risks ---> (PostgreSQL)
```

## Level 3: Knowledge Retrieval & RAG DFD
1. **Query Ingress:** `POST /chat { "query": "What were the risks discussed?" }`
2. **Auth & Context Check:** Core API verifies user session and permission scope (e.g., `tenant_id=xyz`, `role=manager`).
3. **Hybrid Search:** 
   - BM25 on `tsvector` transcript segments.
   - Vector similarity on `pgvector` chunks.
   - Pre-filtered by `tenant_id` and authorized `meeting_ids`.
4. **Reranking:** Cross-Encoder reranks top-K results.
5. **Prompt Assembly:** Guardrailed system prompt + Query + Retrieved Context (with `segment_id` metadata).
6. **LLM Generation:** Model generates answer with inline citations.
7. **Citation Validation:** API matches output citations to injected context.
8. **Egress:** API returns text and validated `transcript_segment_id` arrays to User.
