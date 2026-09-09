from app.repositories.base_tenant import BaseTenantRepository
from app.models.media_asset import MediaAsset
from uuid import UUID
from typing import Optional

class MediaRepository(BaseTenantRepository):
    def get_by_id(self, asset_id: UUID) -> Optional[MediaAsset]:
        return self.session.query(MediaAsset).filter(
            MediaAsset.tenant_id == self.tenant_id,
            MediaAsset.id == asset_id
        ).first()

    def create(self, meeting_id: UUID, filename: str, content_type: str, byte_size: int) -> MediaAsset:
        asset = MediaAsset(
            tenant_id=self.tenant_id, 
            meeting_id=meeting_id,
            filename=filename,
            content_type=content_type,
            byte_size=byte_size
        )
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset
