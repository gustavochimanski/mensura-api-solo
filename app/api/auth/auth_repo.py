# app/api/mensura/repositories/auth_repo.py
from sqlalchemy.orm import Session, joinedload

from app.api.cadastros.models.user_model import UserModel


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> UserModel | None:
        return (
            self.db.query(UserModel)
            .filter(UserModel.username == username)
            .first()
        )

    def get_user_by_id(self, user_id: int) -> UserModel | None:
        return (
            self.db.query(UserModel)
            .options(joinedload(UserModel.empresas))
            .filter(UserModel.id == user_id)
            .first()
        )
