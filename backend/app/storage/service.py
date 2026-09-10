from uuid import UUID
import os

class StorageService:
    @staticmethod
    def generate_raw_key(tenant_id: UUID, meeting_id: UUID, media_id: UUID, extension: str) -> str:
        ext = extension.lstrip(".")
        return f"tenants/{tenant_id}/meetings/{meeting_id}/media/{media_id}/original/source.{ext}"

    @staticmethod
    def generate_derived_key(tenant_id: UUID, meeting_id: UUID, media_id: UUID, suffix: str, extension: str) -> str:
        ext = extension.lstrip(".")
        return f"tenants/{tenant_id}/meetings/{meeting_id}/media/{media_id}/derived/{suffix}.{ext}"
