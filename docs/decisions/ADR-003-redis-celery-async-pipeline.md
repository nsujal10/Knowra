# ADR 003: Redis and Celery Async Pipeline

**Status:** Accepted
**Context:** AI/Media processing blocks sync API threads.
**Options Considered:** RabbitMQ, Apache Kafka, Redis + Celery.
**Decision:** Redis + Celery.
**Consequences:** Established Python ecosystem integration, built-in retry/retry-backoff features, simpler operational footprint than Kafka.
**Migration Trigger:** Requirement for replayable event streams or complex multi-stage fan-out/fan-in topologies.
