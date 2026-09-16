import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user_identity import UserIdentity


class UserIdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_provider_and_id(self, provider: str, provider_user_id: str) -> Optional[UserIdentity]:
        return (
            self.db.query(UserIdentity)
            .filter(
                UserIdentity.provider == provider,
                UserIdentity.provider_user_id == provider_user_id,
            )
            .first()
        )

    def get_by_user_id_and_provider(self, user_id: uuid.UUID, provider: str) -> Optional[UserIdentity]:
        return (
            self.db.query(UserIdentity)
            .filter(
                UserIdentity.user_id == user_id,
                UserIdentity.provider == provider,
            )
            .first()
        )

    def create(
        self,
        user_id: uuid.UUID,
        provider: str,
        provider_user_id: str,
        provider_email: Optional[str] = None,
        metadata_json: Optional[dict] = None,
    ) -> UserIdentity:
        identity = UserIdentity(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            metadata_json=metadata_json,
        )
        self.db.add(identity)
        self.db.flush()
        return identity
