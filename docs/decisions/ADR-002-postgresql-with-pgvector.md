# ADR 002: PostgreSQL with pgvector

**Status:** Accepted
**Context:** Need relational storage and vector similarity search.
**Options Considered:** Postgres + Pinecone, Postgres + Qdrant, Postgres + pgvector.
**Decision:** PostgreSQL 16 with pgvector extension.
**Consequences:** Single system of truth, simplifies backups, allows unified RLS security models over both relational data and embeddings.
**Migration Trigger:** Vector index size exceeds memory limits of standard vertically scaled database instances.
