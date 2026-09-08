# RBAC Matrix

| Capability        | ADMIN | MANAGER | EMPLOYEE |
| :---              | :---: | :---:   | :---:    |
| `users:read`      | ✅    | ✅     | ❌       |
| `users:write`     | ✅    | ❌     | ❌       |
| `meetings:create` | ✅    | ✅     | ✅       |
| `meetings:read`   | ✅    | ✅ (Own/Direct) | ✅ (Own) |
| `actions:update`  | ✅    | ✅     | ✅       |
| `audit:read`      | ✅    | ❌     | ❌       |
| `billing:manage`  | ✅    | ❌     | ❌       |
