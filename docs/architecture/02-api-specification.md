# 02: API Specification

Base Path: `/api/v1`
Auth: Bearer Token (JWT)

## 1. Auth Endpoints
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`

## 2. Meeting Management
### `POST /meetings`
- **Role:** Employee+
- **Body:** `{ "title": "string", "date": "ISO8601" }`
- **Response (201):** `{ "id": "uuid", "upload_url": "string" }`

### `GET /meetings/{id}`
- **Role:** Contextual (Participant or Manager+)
- **Response (200):** Meeting Metadata object.
- **Errors:** 403 Forbidden (RBAC), 404 Not Found.

## 3. Media Ingestion
### `POST /meetings/{id}/process`
- **Role:** Employee+ (Owner)
- **Body:** `{ "media_uri": "s3://..." }`
- **Response (202):** `{ "job_id": "uuid", "status": "PENDING" }`

### `GET /meetings/{id}/status`
- **Response (200):** `{ "status": "PROCESSING", "progress": 45, "step": "DIARIZATION" }`

## 4. Transcript & Intelligence
### `GET /meetings/{id}/transcript`
- **Response (200):** 
```json
{
  "segments": [
    {
      "id": "uuid",
      "speaker_name": "Speaker 1",
      "start_ms": 10500,
      "end_ms": 14200,
      "text": "Let's finalize the architecture."
    }
  ]
}
```

### `GET /meetings/{id}/summary`
### `GET /meetings/{id}/decisions`
### `GET /meetings/{id}/actions`
### `GET /meetings/{id}/risks`

## 5. Search & AI
### `POST /chat`
- **Body:** `{ "meeting_ids": ["uuid"], "query": "string" }`
- **Response (200):**
```json
{
  "answer": "The architecture was finalized [1].",
  "citations": [
    { "ref": "1", "segment_id": "uuid", "text": "Let's finalize..." }
  ]
}
```
