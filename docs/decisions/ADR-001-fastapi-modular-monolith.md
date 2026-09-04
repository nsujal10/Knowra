# ADR 001: FastAPI Modular Monolith

**Status:** Accepted
**Context:** The platform requires an API for sync operations and async dispatch.
**Options Considered:** Microservices, Django, FastAPI Modular Monolith.
**Decision:** Adopt FastAPI as a Modular Monolith. 
**Consequences:** High performance for async IO, automatic OpenAPI docs, low initial deployment complexity. Enforces strict internal module boundaries.
**Migration Trigger:** When a specific domain (e.g., search) requires independent scaling beyond the core API's capacity.
