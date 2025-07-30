# app/mensura/repositories/auth_repo.py
from sqlalchemy.orm import Session

from app.api.mensura.models.user_model import UserModel


class authRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_username(self, username: str) -> UserModel | None:
        """ Retorna o usuário pelo username, ou None se não existir."""
        return self.db.query(UserModel).filter(UserModel.username == username).first()

    def get_user_by_id(self, user_id: int) -> UserModel | None:
        """ Retorna o usuário pelo username, ou None se não existir."""
        return self.db.query(UserModel).filter(UserModel.id == user_id).first()

