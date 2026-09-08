from app.repositories.base import BaseRepository
from app.models.membership import Membership

class MembershipRepository(BaseRepository):
    def get_by_user_id(self, user_id) -> Membership | None:
        # Assuming single membership for MVP
        return self.session.query(Membership).filter(Membership.user_id == user_id, Membership.is_active == True).first()
