# Multi-Tenancy Architecture

## Isolation Strategy
The Knowra platform utilizes a **Shared Database, Shared Schema** multi-tenancy model. 
Every tenant-scoped table includes a `tenant_id` foreign key referencing the `organizations.id` table.

## Defense in Depth
Tenant isolation is enforced at four independent layers:
1. **API / Routing Layer**: Extracts `tenant_id` securely from the authenticated JWT (via `CurrentUserContext.organization_id`). Client-provided `tenant_id` fields in JSON payloads or URLs are strictly rejected or ignored.
2. **Service / Repository Layer**: All data access queries enforce `tenant_id` as a mandatory keyword argument. The repository methods append `.filter(Model.tenant_id == tenant_id)`.
3. **Database Layer (RLS)**: PostgreSQL Row-Level Security (RLS) acts as a fail-safe. Active database sessions receive `SET LOCAL app.current_tenant = 'uuid'` and policies enforce `USING (tenant_id = current_setting('app.current_tenant')::uuid)`.
4. **Storage Layer**: MinIO object paths are strictly prefixed with `tenants/{tenant_id}/`. Access requires server-side presigned URL generation, which verifies database ownership before issuing the URL.
