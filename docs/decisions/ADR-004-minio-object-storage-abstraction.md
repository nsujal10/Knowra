# ADR 004: MinIO Object Storage Abstraction

**Status:** Accepted
**Context:** Need scalable media storage mimicking cloud environments locally.
**Options Considered:** Local File System, direct AWS S3, MinIO.
**Decision:** MinIO configured identically to S3 API.
**Consequences:** Enables local, air-gapped development while maintaining 100% compatibility with AWS S3 for production deployment.
**Migration Trigger:** Production rollout to AWS/GCP (swap endpoints via environment variables).
