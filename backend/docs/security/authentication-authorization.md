# Authentication & Authorization Architecture

## 1. Multi-Tenancy Boundary
Multi-tenancy is organization-based. `Organization` equals `Tenant`. A user is linked to an organization via a `Membership`.
The `tenant_id` is derived strictly from the server-verified JWT and database membership state, not from client headers.

## 2. Token & Session Architecture
- **Access Token:** Short-lived JWT (15 minutes). Signed using HS256. Contains `sub` (user ID), `sid` (session ID), `org` (organization ID).
- **Refresh Token:** 256-bit opaque string (URL-safe base64), valid for 7 days. Stored as a SHA-256 hash in the `refresh_sessions` table.

## 3. Token Rotation & Reuse Detection
When a refresh token is used:
1. System hashes the provided token and looks it up.
2. If `revoked_at` is set: **Breach detected**. The token was already used. The system revokes the entire token family (all sessions for the user) and logs an audit event.
3. If valid: The token is marked revoked, a new token is generated, and its hash is linked via `replaced_by`.

## 4. Passwords
Stored using `bcrypt` with a work factor of 12. Errors always return generic "Invalid credentials".
