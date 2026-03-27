from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import User


class AuthUserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> User | None:
        return self.db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

    def add(self, user: User) -> None:
        self.db.add(user)

    def commit(self) -> None:
        self.db.commit()
