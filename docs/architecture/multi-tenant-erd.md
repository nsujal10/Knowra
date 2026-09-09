# Multi-Tenant Entity Relationship Diagram

```text
+----------------+       +-------------------+
| Organizations  |       | Users             |
| (Tenants)      |       |                   |
+----------------+       +-------------------+
| id (UUID) PK   |<------+ id (UUID) PK      |
| name           |       | email             |
+-------+--------+       +--------+----------+
        |                         |
        |    +--------------------+
        |    | Memberships
        |    +--------------------+
        +--->| organization_id FK
             | user_id FK
             | role_id FK
             +--------------------+

(Tenant-Owned Entities - Enforced via RLS and Repository Layer)

+----------------+       +-------------------+       +-------------------+
| Meetings       |       | MediaAssets       |       | ProcessingJobs    |
+----------------+       +-------------------+       +-------------------+
| id PK          |       | id PK             |       | id PK             |
| tenant_id FK   |<--+   | tenant_id FK      |<--+   | tenant_id FK      |<--+
| owner_id FK    |   |   | meeting_id FK     |   |   | meeting_id FK     |   |
| title          |   |   | file_path         |   |   | status            |   |
+----------------+   |   +-------------------+   |   +-------------------+   |
                     |                           |                           |
                     +---------------------------+---------------------------+
                     |
            (FOREIGN KEY to Organizations.id)
```
