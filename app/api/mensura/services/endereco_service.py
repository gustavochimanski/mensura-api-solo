from sqlalchemy.orm import Session
from fastapi import HTTPException
import re

from app.api.delivery.repositories.cliente_repo import ClienteRepository
from app.api.mensura.repositories.endereco_repo import EnderecoRepository
from app.api.mensura.schemas.endereco_schema import EnderecoCreate, EnderecoUpdate
from app.api.mensura.models.endereco_model import EnderecoModel

class EnderecoService:
    def __init__(self, db: Session):
        self.repo = EnderecoRepository(db)
        self.repo_cliente = ClienteRepository(db)

    def get_endereco(self, id: int):
        endereco = self.repo.get(id)
        if not endereco:
            raise HTTPException(status_code=404, detail="Endereço não encontrado")
        return endereco

    def list_enderecos(self, skip: int = 0, limit: int = 100):
        return self.repo.list(skip, limit)

    def create_endereco(self, data: EnderecoCreate):
        # 🔍 Valida cliente
        cliente = self.repo_cliente.get(data.cliente_id)
        if not cliente:
            raise HTTPException(status_code=400, detail="Cliente não encontrado")

        # 🧹 Valida formato do CEP
        if not self._is_cep_valido(data.cep):
            raise HTTPException(status_code=400, detail="CEP inválido")

        # 🛑 (Opcional) Verifica duplicidade do endereço para o mesmo cliente
        if self.repo.exists_for_cliente(data.cliente_id, data.cep, data.logradouro, data.numero):
            raise HTTPException(status_code=400, detail="Endereço já cadastrado para este cliente")

        endereco = EnderecoModel(**data.dict())
        return self.repo.create(endereco)

    def update_endereco(self, id: int, data: EnderecoUpdate):
        endereco = self.get_endereco(id)

        payload = data.dict(exclude_unset=True)

        # Se vai alterar cliente, valida existência
        if "cliente_id" in payload:
            cliente = self.repo_cliente.get(payload["cliente_id"])
            if not cliente:
                raise HTTPException(status_code=400, detail="Cliente não encontrado")

        # Se vai alterar CEP, valida formato
        if "cep" in payload and not self._is_cep_valido(payload["cep"]):
            raise HTTPException(status_code=400, detail="CEP inválido")

        return self.repo.update(endereco, payload)

    def delete_endereco(self, id: int):
        endereco = self.get_endereco(id)
        self.repo.delete(endereco)

    def _is_cep_valido(self, cep: str) -> bool:
        return bool(re.fullmatch(r"\d{5}-?\d{3}", cep))
