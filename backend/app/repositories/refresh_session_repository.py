from app.repositories.base import BaseRepository
from app.models.refresh_session import RefreshSession

class RefreshSessionRepository(BaseRepository):
    def get_by_hash(self, token_hash: str) -> RefreshSession | None:
        return self.session.query(RefreshSession).filter(RefreshSession.token_hash == token_hash).first()
