# app/api/mensura/services/endereco_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.mensura.repositories.endereco_repo import EnderecoRepository
from app.api.mensura.schemas.endereco_schema import EnderecoCreate, EnderecoUpdate


class EnderecoService:
    def __init__(self, db: Session):
        self.repo = EnderecoRepository(db)

    # Nomes "canônicos"
    def list(self, skip: int = 0, limit: int = 100):
        return self.repo.list(skip, limit)

    def get(self, id_: int):
        addr = self.repo.get(id_)
        if not addr:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Endereço não encontrado")
        return addr

    def create(self, data: EnderecoCreate):
        return self.repo.create(**data.model_dump(exclude_unset=True))

    def update(self, id_: int, data: EnderecoUpdate):
        addr = self.get(id_)
        return self.repo.update(addr, **data.model_dump(exclude_none=True))

    def delete(self, id_: int):
        addr = self.get(id_)
        self.repo.delete(addr)
        return {"ok": True}

    # Aliases para compatibilizar com router existentes
    def list_enderecos(self, skip: int = 0, limit: int = 100):
        return self.list(skip, limit)

    def get_endereco(self, id_: int):
        return self.get(id_)

    def create_endereco(self, data: EnderecoCreate):
        return self.create(data)

    def update_endereco(self, id_: int, data: EnderecoUpdate):
        return self.update(id_, data)

    def delete_endereco(self, id_: int):
        return self.delete(id_)
