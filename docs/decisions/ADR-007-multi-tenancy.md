# ADR 007: Shared-Table Multi-Tenancy with PostgreSQL RLS

**Status:** Accepted
**Context:** Knowra requires multi-tenancy. Database per tenant is too operationally complex for MVP. Schema per tenant breaks connection pooling limits rapidly.
**Decision:** Adopt a Shared Database, Shared Schema architecture. Every tenant resource will have a `tenant_id`. We will use PostgreSQL Row-Level Security (RLS) as a defense-in-depth safety net below the application ORM.
**Consequences:** 
- Highly scalable and resource-efficient.
- Requires strict developer discipline: repositories MUST filter by `tenant_id`.
- Requires a custom database dependency to `SET LOCAL app.current_tenant` per transaction.
