from sqlalchemy.orm import Session


class BaseRepository:
    """
    Base repository providing a SQLAlchemy session.
    Domain-specific repositories inherit from this class.
    """

    def __init__(self, db: Session):
        self.session = db