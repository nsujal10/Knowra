# ADR 005: Local ASR and Diarization

**Status:** Accepted
**Context:** Transcribing and diarizing highly sensitive enterprise meetings.
**Options Considered:** SaaS APIs (AssemblyAI, Deepgram), Local Models (Whisper/Pyannote).
**Decision:** Local execution of `faster-whisper` and `pyannote.audio`.
**Consequences:** Guarantees zero data leakage to third-party sub-processors. Requires GPU provisioning for worker nodes.
**Migration Trigger:** Latency requirements demand streaming API offload, provided security/compliance approves SaaS vendors.
