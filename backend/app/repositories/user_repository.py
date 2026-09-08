from app.repositories.base import BaseRepository
from app.models.user import User

class UserRepository(BaseRepository):
    def get_by_email(self, email: str) -> User | None:
        return self.session.query(User).filter(User.email == email).first()
        
    def get_by_id(self, user_id) -> User | None:
        return self.session.query(User).filter(User.id == user_id).first()
