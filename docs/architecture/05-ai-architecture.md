# 05: AI Architecture

## 1. Speech-to-Text (ASR)
- **Engine:** `faster-whisper` (CTranslate2).
- **Model:** Large-v3.
- **Compute:** FP16 on GPU (CUDA), INT8 fallback on CPU.
- **Config:** Beam size=5, VAD filter=True (Silero VAD) to remove silence.

## 2. Diarization Engine
- **Engine:** `pyannote.audio` 3.0.
- **Pipeline:** Speaker Diarization + Clustering.
- **Alignment logic:** Merge Whisper word-level timestamps with Pyannote speaker segments using temporal intersection over union (IoU).

## 3. Structured Intelligence Extraction
- **Engine:** LLM via API (e.g., GPT-4o / Claude 3.5 Sonnet).
- **Output:** Strict JSON schema via function calling / structured outputs.
- **Validation:** Pydantic models in Python enforce schema correctness before database insertion.
- **Artifacts:** Summaries, Decisions, Action Items, Risks.

## 4. RAG & Search Fabric
### 4.1 Semantic Chunking
- **Strategy:** Speaker-turn boundary chunking with a sliding window (e.g., 300 tokens overlap). Ensures chunks retain conversational context without breaking sentences mid-way.

### 4.2 Embedding Engine
- **Model:** `text-embedding-3-small` (1536 dimensions) or equivalent standard.

### 4.3 Hybrid Search
- **Mechanism:** PostgreSQL `tsvector` (BM25) combined with `pgvector` HNSW index (Cosine Similarity).
- **Fusion:** Reciprocal Rank Fusion (RRF) normalizes and combines scores from both vectors.

### 4.4 Prompt Construction & Guardrails
- **Prompt Isolation:** 
  ```text
  [SYSTEM]: You are a corporate assistant. Use only the provided context.
  [CONTEXT]: <Filtered Transcript Data>
  [USER]: <Query>
  ```
- Guardrails prevent execution of instructions found within the `<Filtered Transcript Data>`.

### 4.5 Citation Engine
- Context injection includes segment identifiers `[SEG_ID: uuid]`. Model is prompted to output `... statement [SEG_ID: uuid]`. Post-processing parses these and maps them to exactly precise `start_time_ms` for UI video playback.
