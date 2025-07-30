# app/api/mensura/services/cliente_service.py
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.repositories.cliente_repo import ClienteRepository
from app.api.delivery.schemas.cliente_schema import ClienteCreate, ClienteUpdate


class ClienteService:
    def __init__(self, db: Session):
        self.repo = ClienteRepository(db)

    def get_cliente(self, id: int):
        cliente = self.repo.get(id)
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        return cliente

    def list_clientes(self, skip: int = 0, limit: int = 100):
        return self.repo.list(skip, limit)

    def create_cliente(self, data: ClienteCreate):
        novo = ClienteDeliveryModel(**data.dict())
        return self.repo.create(novo)

    def update_cliente(self, id: int, data: ClienteUpdate):
        cliente = self.get_cliente(id)
        return self.repo.update(cliente, data.dict(exclude_unset=True))

    def delete_cliente(self, id: int):
        cliente = self.get_cliente(id)
        self.repo.delete(cliente)
