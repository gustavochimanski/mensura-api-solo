from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.api.mensura.repositories.endereco_repo import EnderecoRepository
from app.api.mensura.schemas.endereco_schema import EnderecoCreate, EnderecoUpdate
from app.api.mensura.models.endereco_model import EnderecoModel

class EnderecoService:
    def __init__(self, db: Session):
        self.repo = EnderecoRepository(db)

    def get_endereco(self, id: int):
        endereco = self.repo.get(id)
        if not endereco:
            raise HTTPException(status_code=404, detail="Endereco not found")
        return endereco

    def list_enderecos(self, skip: int = 0, limit: int = 100):
        return self.repo.list(skip, limit)

    def create_endereco(self, data: EnderecoCreate):
        endereco = EnderecoModel(**data.dict())
        return self.repo.create(endereco)

    def update_endereco(self, id: int, data: EnderecoUpdate):
        endereco = self.get_endereco(id)
        return self.repo.update(endereco, data.dict(exclude_unset=True))

    def delete_endereco(self, id: int):
        endereco = self.get_endereco(id)
        self.repo.delete(endereco)