from typing import List, Optional
from sqlalchemy.orm import Session
from app.api.mensura.models.user_model import UserModel

class UsuarioRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.id == id).first()

    def get_by_username(self, username: str) -> Optional[UserModel]:
        return self.db.query(UserModel).filter(UserModel.username == username).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        return self.db.query(UserModel).offset(skip).limit(limit).all()

    def create(self, user: UserModel) -> UserModel:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)  # 👈 estava sem o argumento!
        return user

    def update(self, user: UserModel, data: dict) -> UserModel:
        for key, value in data.items():
            setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def delete(self, user: UserModel) -> None:
        self.db.delete(user)
        self.db.commit()
