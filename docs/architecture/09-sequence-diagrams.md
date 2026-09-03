# 09: Sequence Diagrams

## 1. Meeting Upload & Validation Flow
```text
Client            API             MinIO             DB             Redis
  |                |                |               |                |
  |-- POST /upload |                |               |                |
  |                |-- Val Token -->|               |                |
  |                |-- Put Object ->|               |                |
  |                |                |-- Insert(P) ->|                |
  |                |                |               |-- Enqueue() -->|
  |<-- 202 JobID --|                |               |                |
```
*State:* `UPLOADED` -> `PENDING`

## 2. Asynchronous Processing Pipeline
```text
Redis            Worker            MinIO             DB           LLM API
  |                |                 |               |               |
  |-- Dequeue() -->|                 |               |               |
  |                |-- Update State (PROCESSING) --->|               |
  |                |-- Get Audio --->|               |               |
  |                |-- FFmpeg()      |               |               |
  |                |-- Whisper()     |               |               |
  |                |-- Diarize()     |               |               |
  |                |-- Align()       |               |               |
  |                |                 |-- Save Transcript ----------> |
  |                |                 |               |               |
  |                |-- Extract Metadata ---------------------------->|
  |                |                 |               |<-- JSON Resp -|
  |                |                 |-- Save Intel. |               |
  |                |-- Update State (COMPLETED) ---->|               |
```

## 3. RAG Search & Q&A
```text
Client            API               DB (pgvector)         LLM API
  |                |                     |                   |
  |-- POST /chat ->|                     |                   |
  |                |-- Verify RBAC()     |                   |
  |                |-- Embed Query()     |                   |
  |                |-- Hybrid Search() ->|                   |
  |                |<-- Return Chunks ---|                   |
  |                |-- Assembly Prompt() |                   |
  |                |-- Generate() -------------------------->|
  |                |<-- Response + Cites --------------------|
  |                |-- Validate Cites()  |                   |
  |<-- 200 OK -----|                     |                   |
```

## 4. Failure & Retry Circuit
```text
Worker            Redis              DB
  |                 |                |
  |-- Error()       |                |
  |-- Retry++       |                |
  |-- if Retry < 3: |-- Requeue() -->|
  |-- else:         |-- Push DLQ --->|
  |                 |                |-- State=FAILED
```
