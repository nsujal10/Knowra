from app.repositories.base import BaseRepository
from app.models.role import Role

class RoleRepository(BaseRepository):
    def get_by_code(self, code: str) -> Role | None:
        return self.session.query(Role).filter(Role.code == code).first()
