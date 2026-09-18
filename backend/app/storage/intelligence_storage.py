from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from app.storage.minio import get_storage_client

logger = structlog.get_logger(__name__)

DERIVED_BUCKET = "knowra-derived"


class IntelligenceStorageService:
    """Handles tenant-isolated artifact retrieval and persistence in MinIO."""

    def __init__(self, tenant_id: UUID) -> None:
        self.tenant_id = str(tenant_id)
        self.storage = get_storage_client()

    def get_transcript_s3_key(self, meeting_id: UUID) -> str:
        return f"tenants/{self.tenant_id}/meetings/{meeting_id}/transcription/transcript.json"

    def get_intelligence_s3_key(self, meeting_id: UUID, run_id: UUID) -> str:
        return f"tenants/{self.tenant_id}/meetings/{meeting_id}/intelligence/{run_id}.json"

    def fetch_transcript_json(self, meeting_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Download transcript JSON using an isolated temporary scratch workspace.
        Guarantees zero file overwrite collisions across concurrent Celery worker processes.
        """
        s3_key = self.get_transcript_s3_key(meeting_id)
        log = logger.bind(tenant_id=self.tenant_id, meeting_id=str(meeting_id), s3_key=s3_key)

        with tempfile.TemporaryDirectory(prefix=f"knowra_transcript_{meeting_id}_") as tmpdir:
            local_path = os.path.join(tmpdir, "transcript.json")
            download_ok = self.storage.download_file(DERIVED_BUCKET, s3_key, local_path)

            if not download_ok or not os.path.exists(local_path):
                log.warning("Transcript artifact not found in object storage")
                return None

            try:
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data
            except (json.JSONDecodeError, OSError) as err:
                log.error("Failed to read downloaded transcript JSON", error=str(err))
                raise RuntimeError(f"Corrupted transcript JSON in storage: {s3_key}") from err

    def persist_intelligence_json(
        self, meeting_id: UUID, run_id: UUID, payload: Dict[str, Any]
    ) -> str:
        """
        Atomically serialize and upload the extraction results to MinIO.
        Returns the derived S3 key.
        """
        s3_key = self.get_intelligence_s3_key(meeting_id, run_id)
        log = logger.bind(tenant_id=self.tenant_id, meeting_id=str(meeting_id), run_id=str(run_id))

        with tempfile.TemporaryDirectory(prefix=f"knowra_intel_{run_id}_") as tmpdir:
            local_path = os.path.join(tmpdir, "intelligence.json")
            with open(local_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)

            upload_ok = self.storage.upload_file(
                bucket=DERIVED_BUCKET,
                key=s3_key,
                file_path=local_path,
                content_type="application/json",
            )
            if not upload_ok:
                raise RuntimeError(f"Failed to persist intelligence JSON to {s3_key}")

        log.info("Persisted intelligence artifact successfully", s3_key=s3_key)
        return s3_key
