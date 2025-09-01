from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.api.delivery.repositories.repo_cliente import ClienteRepository
from app.api.delivery.schemas.schema_cliente import ClienteCreate, ClienteUpdate

class ClienteService:
    def __init__(self, db: Session):
        self.repo = ClienteRepository(db)

    def get_current(self, token: str):
        cli = self.repo.get_by_token(token)
        if not cli:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")
        return cli

    def create(self, data: ClienteCreate):
        # verifica telefone duplicado
        existing = None
        if data.telefone:
            existing = self.repo.get_by_telefone(data.telefone)
            if existing:
                return existing  # retorna o cliente já cadastrado

        # cria um novo cliente se não existir
        return self.repo.create(**data.model_dump(exclude_unset=True))

    def update(self, token: str, data: ClienteUpdate):
        db_obj = self.repo.get_by_token(token)
        if not db_obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não existe")
        return self.repo.update(db_obj, **data.model_dump(exclude_none=True))

    def set_ativo(self, token: str, on: bool):
        obj = self.repo.set_ativo(token, on)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não existe")
        return obj
