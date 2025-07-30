from typing import List

from sqlalchemy.orm import Session

from app.api.mensura.models.user_model import UserModel
from app.database.db_connection import Base


class UsuarioRepository(Base):
    def __init__(self, db: Session):
        self.db = db

    def get(self, id : int) -> UserModel:
        return self.db.query(UserModel).filter(UserModel.id == id).first()

    def list(self, skip: int = 0, limit: int = 0) -> List[UserModel]:
        return self.db.query(UserModel).offset(skip).limit(limit).all()

    def create(self, user: UserModel) -> UserModel:
        self.db.add(user)
        self.db.commit()
        self.db.refresh()
        return user

    def update(self, user: UserModel, data: dict) -> UserModel:
        for key, value in data.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: UserModel):
        self.db.delete(user)
        self.db.commit()