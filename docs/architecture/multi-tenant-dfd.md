# Multi-Tenant Data Flow

## Level 0: Ingress & Context
```text
[Client] ---> (HTTP Request w/ JWT) ---> [FastAPI Gateway]
                                                |
                                      (JWT Validation & Extraction)
                                                |
                                     [Context: tenant_id = X]
```

## Level 1: Secure Data Access
```text
[FastAPI Gateway] ---> (Route Handler)
                             |
                             v
                 [Dependency: get_tenant_db]
                 (Executes SET LOCAL app.current_tenant = X)
                             |
                             v
                  [Tenant-Aware Service]
                  (Injects tenant_id=X into Repository call)
                             |
                             v
                 [Tenant-Aware Repository]
                 (Query: SELECT ... WHERE tenant_id = X)
                             |
                             v
                   [PostgreSQL Engine]
                (Enforces RLS Policy: tenant_id = X)
                             |
                             v
                    (Sanitized Results)
```
