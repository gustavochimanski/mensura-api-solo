# app/api/mensura/repositories/endereco_repo.py
from typing import List, Optional
from sqlalchemy.orm import Session

from app.api.mensura.models.endereco_model import EnderecoModel


class EnderecoRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, skip: int = 0, limit: int = 100) -> List[EnderecoModel]:
        q = self.db.query(EnderecoModel).offset(skip)
        if limit:
            q = q.limit(limit)
        return q.all()

    def get(self, id_: int) -> Optional[EnderecoModel]:
        return self.db.get(EnderecoModel, id_)

    def create(self, **data) -> EnderecoModel:
        addr = EnderecoModel(**data)
        self.db.add(addr)
        self.db.commit()
        self.db.refresh(addr)
        return addr

    def update(self, addr: EnderecoModel, **data) -> EnderecoModel:
        for f, v in data.items():
            setattr(addr, f, v)
        self.db.commit()
        self.db.refresh(addr)
        return addr

    def delete(self, addr: EnderecoModel):
        self.db.delete(addr)
        self.db.commit()
