from typing import Optional, List

from sqlalchemy.orm import Session

from app.api.mensura.models.endereco_model import EnderecoModel


class EnderecoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Optional[EnderecoModel]:
        return self.db.query(EnderecoModel).filter(EnderecoModel.id == id).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[EnderecoModel]:
        return self.db.query(EnderecoModel).offset(skip).limit(limit).all()

    def create(self, endereco: EnderecoModel) -> EnderecoModel:
        self.db.add(endereco)
        self.db.commit()
        self.db.refresh(endereco)
        return endereco

    def update(self, endereco: EnderecoModel, data: dict) -> EnderecoModel:
        for key, value in data.items():
            setattr(endereco, key, value)
        self.db.commit()
        self.db.refresh(endereco)
        return endereco

    def delete(self, endereco: EnderecoModel):
        self.db.delete(endereco)
        self.db.commit()