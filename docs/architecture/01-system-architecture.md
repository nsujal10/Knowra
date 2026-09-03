# 01: System Architecture

## 1. High-Level Topology

```text
       [ Next.js Web Client ]
                | (HTTPS / REST)
                v
       +--------------------+
       |  API Gateway /     |
       |  Modular Core      |<---- (Reads/Writes) ----> [ PostgreSQL 16 (Relational + pgvector) ]
       |  (FastAPI)         |                                 ^
       +--------------------+                                 |
           |             |                                    |
     (Task Enqueue)  (S3 Upload/Download)                     |
           v             v                                    |
    [ Redis Broker ]  [ MinIO / S3 ] <--- (Media Pull) ---+   | (DB Read/Write via ORM/SQL)
           ^             (Storage Fabric)                 |   |
           |                                              |   |
     (Task Dequeue)                                       |   |
           |                                              |   |
           v                                              |   v
       +-------------------------------------------------------------+
       |                  Asynchronous Worker Pool                   |
       |  +-------------+  +--------------+  +------------------+    |
       |  | Media/Audio |  | ASR & Diar.  |  | LLM & Indexing   |    |
       |  | (FFmpeg)    |  | (Whisper/    |  | (RAG, Chunking)  |    |
       |  |             |  |  Pyannote)   |  |                  |    |
       |  +-------------+  +--------------+  +------------------+    |
       +-------------------------------------------------------------+
```

## 2. Component Breakdown

### 2.1 Frontend (Next.js Client)
- **Role:** User interface for meeting upload, transcript viewing, intelligence dashboards, and chat Q&A.
- **Protocol:** HTTPS, REST over JSON.

### 2.2 API Gateway / Modular Core (FastAPI)
- **Role:** Handles routing, authentication, RBAC authorization, rate limiting, and request validation.
- **Tech Stack:** Python, FastAPI, Pydantic, SQLAlchemy.
- **Scaling:** Horizontally scalable, stateless containers.

### 2.3 Task Broker & Cache (Redis)
- **Role:** Message queuing for Celery tasks, ephemeral state caching, rate limit counters.
- **Topics:** `transcription_queue`, `intelligence_queue`, `indexing_queue`, `dlq`.

### 2.4 Asynchronous Worker Pool
- **Media Worker:** FFmpeg audio extraction and normalization (16kHz, mono).
- **ASR/Diarization Worker:** GPU-accelerated faster-whisper and pyannote.audio.
- **LLM/Indexing Worker:** Extractive intelligence (summaries/actions) and chunking/embedding generation using external LLM APIs (e.g., OpenAI/Anthropic) and embedding models.

### 2.5 Storage Fabric
- **Object Storage (MinIO/S3):** Immutable storage for raw video/audio and normalized audio files.
- **Relational DB (PostgreSQL 16):** Canonical state, user/tenant mappings, RBAC tables, transcripts, intelligence artifacts.
- **Vector DB (pgvector):** Colocated in PostgreSQL for embedding storage and hybrid search (BM25 + Cosine Similarity).

## 3. Boundaries & Scaling
- **Service Boundaries:** API handles synchronous UI interactions; Workers handle asynchronous heavy lifting.
- **Scaling:** API scales on CPU/Memory; Workers scale on GPU (ASR/Diarization) or CPU/Network (LLM inference).
