# Multi-Tenant Threat Model

| Threat Vector | Attack Description | Mitigation Strategy | Test Coverage |
| :--- | :--- | :--- | :--- |
| 1. Cross-tenant Read | Tenant A guesses Tenant B's meeting UUID and attempts a GET request. | Repositories mandate `tenant_id` filtering. API returns 404 Not Found to prevent data exposure. | `test_tenant_isolation_api.py` |
| 2. Cross-tenant Write | Tenant A attempts to update/delete Tenant B's meeting. | Service layer validates ownership via repository before committing mutations. Returns 404. | `test_tenant_isolation_api.py` |
| 3. IDOR via Foreign Key | Tenant A creates a MediaAsset attaching it to Tenant B's meeting. | API/Service layer strictly fetches the parent meeting using Tenant A's context before attachment. | `test_tenant_isolation_api.py` |
| 4. Forged Tenant Headers | Attacker injects `X-Tenant-ID: <target_uuid>` to spoof context. | Middleware/Dependency ignores headers. `tenant_id` is cryptographically extracted from the signed JWT payload. | `test_tenant_isolation_api.py` |
| 5. Payload Injection | Attacker sends `{"tenant_id": "<target_uuid>"}` in POST body. | Pydantic schemas omit `tenant_id`. Service layer forcibly overwrites any DB model assignment with `CurrentUserContext`. | `test_tenant_isolation_api.py` |
| 6. Storage Path Tampering | Attacker attempts directory traversal to access foreign S3 bucket paths. | Storage API completely abstracts paths. Clients never specify the path; the server deterministically generates it. | `test_tenant_storage_isolation.py` |
| 7. Presigned URL Forgery | Attacker asks for a presigned URL of an asset they don't own. | Endpoint queries asset via `tenant_id` repository method before invoking MinIO client. | `test_tenant_storage_isolation.py` |
| 8. Celery Context Confusion | Worker executes a job on Tenant B's data using Tenant A's configuration. | Tasks carry `tenant_id` in payload and independently verify DB state before executing. | `test_worker_tenant_validation.py` |
| 9. Postgres Connection Leak | RLS context persists to subsequent queries in a connection pool. | `SET LOCAL` is used (scoped to transaction), and a `RESET app.current_tenant` is enforced in the `finally` block of the session generator. | `test_postgres_rls.py` |
| 10. Vector Search Leakage | RAG pipeline retrieves semantic chunks from foreign organizations. | pgvector queries explicitly include `WHERE tenant_id = :tenant_id` prior to nearest-neighbor calculation. | Phase 8 Expansion |
