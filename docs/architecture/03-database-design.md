# 03: Database Design

## PostgreSQL 16 Schema with pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Core Tenants
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users & RBAC
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('Employee', 'Manager', 'Executive', 'Admin', 'Knowledge_Admin')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Meetings (System of Record)
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    meeting_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Canonical Transcript
CREATE TABLE transcript_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    speaker_label VARCHAR(100),
    start_time_ms INTEGER NOT NULL,
    end_time_ms INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Intelligence Artifacts
CREATE TABLE meeting_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    assignee_name VARCHAR(255),
    description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'OPEN',
    source_segment_ids UUID[]
);

-- Vector Chunks
CREATE TABLE retrieval_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    segment_ids UUID[] NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536) NOT NULL
);

-- Indexes
CREATE INDEX idx_meetings_tenant ON meetings(tenant_id);
CREATE INDEX idx_transcript_meeting ON transcript_segments(meeting_id);
CREATE INDEX idx_retrieval_chunks_tenant_meeting ON retrieval_chunks(tenant_id, meeting_id);
CREATE INDEX idx_chunks_embedding ON retrieval_chunks USING hnsw (embedding vector_cosine_ops);

-- RLS Enforcement
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON meetings
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```
