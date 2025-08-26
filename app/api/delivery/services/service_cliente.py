from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.delivery.repositories.repo_cliente import ClienteRepository
from app.api.delivery.schemas.schema_cliente import ClienteUpdate, ClienteCreate

class ClienteService:
    def __init__(self, db: Session):
        self.repo = ClienteRepository(db)

    def get_current(self):
        cli = self.repo.get_current()
        if not cli:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
        return cli

    def create(self, data: ClienteCreate):
        # poderia validar cpf/email únicos aqui
        return self.repo.create(**data.model_dump(exclude_unset=True))

    def update(self, number_client: int, data: ClienteUpdate):
        db_obj = self.repo.get_by_id(number_client)
        if not db_obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não existe")
        return self.repo.update(db_obj, **data.model_dump(exclude_none=True))

    def set_ativo(self, number_client: int, on: bool):
        obj = self.repo.set_ativo(number_client, on)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não existe")
        return obj
