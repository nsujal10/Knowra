# Technology Stack

## Technology Matrix
| Category | MVP Decision | Version | Responsibility | Long-Term Evolution |
| :--- | :--- | :--- | :--- | :--- |
| **Core API** | FastAPI | 0.110.x | Sync HTTP routing, auth, RBAC, input validation. | Split off heavy domains into microservices if needed. |
| **Database** | PostgreSQL | 16 | Relational state, tenant isolation (RLS). | Managed Cloud SQL / Aurora. |
| **Vector DB** | pgvector | 0.6.x | Embedding storage, hybrid search (HNSW/BM25). | Dedicated Vector DB (Milvus/Qdrant) at high scale. |
| **Message Broker** | Redis | 7.x | Celery queue management, ephemeral caching. | Kafka/Redpanda for event sourcing. |
| **Task Runner** | Celery | 5.3.x | Decoupled async media/AI processing. | Kubernetes Jobs / Temporal workflows. |
| **Object Storage** | MinIO | LATEST | S3-compatible immutable media blob storage. | AWS S3 / Azure Blob Storage. |
| **Frontend** | Next.js | 14.x | React web client, dashboard UI, chat interface. | Distributed micro-frontends. |
| **ASR** | faster-whisper | Large-v3 | Speech-to-text inference. | Finetuned customized Whisper variants. |
| **Diarization** | pyannote.audio | 3.x | Speaker segmentation and clustering. | Multimodal/video-based diarization. |

## Technology Responsibility Map
- **FastAPI:** Sole entry point for user requests. NEVER blocks on AI inference or video encoding.
- **PostgreSQL (pgvector):** Single source of truth. Handles relational consistency and vector nearest-neighbor lookups securely within the same transaction boundary.
- **MinIO:** Stores raw `.mp4`/`.wav` files and intermediate processed FLACs.
- **Redis & Celery:** Buffers heavy compute. Ensures zero lost jobs through acknowledgment mechanisms.
- **Next.js:** Handles client-side state and visualization only.

## Deferred Technologies (MVP Exclusions)
- **Kafka:** Overkill for simple A -> B task processing; Celery + Redis is sufficient.
- **Kubernetes:** Adds orchestration overhead.
- **Dedicated Vector DBs (Milvus/Qdrant):** pgvector handles millions of rows effectively; defers architectural complexity of synchronizing two separate data stores.
- **Terraform:** MVP focuses on reproducible application layers (Docker Compose) rather than cloud provisioning.
