from __future__ import annotations
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.api.delivery.repositories.repo_entregadores import EntregadorRepository
from app.api.delivery.schemas.schema_entregador import EntregadorCreate, EntregadorUpdate

class EntregadoresService:
    def __init__(self, db: Session):
        self.repo = EntregadorRepository(db)

    def list(self):
        return self.repo.list()

    def get(self, id_: int):
        obj = self.repo.get(id_)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Entregador não encontrado")
        return obj

    def create(self, data: EntregadorCreate):
        return self.repo.create_with_empresa(**data.model_dump(exclude_unset=True))

    def update(self, id_: int, data: EntregadorUpdate):
        obj = self.get(id_)
        return self.repo.update(obj, **data.model_dump(exclude_none=True))

    def vincular_empresa(self, entregador_id: int, empresa_id: int):
        # primeiro garante que o entregador existe
        self.get(entregador_id)
        self.repo.vincular_empresa(entregador_id, empresa_id)
        return self.get(entregador_id)  # retorna o entregador atualizado

    def delete(self, id_: int):
        obj = self.get(id_)
        self.repo.delete(obj)
        return {"ok": True}
