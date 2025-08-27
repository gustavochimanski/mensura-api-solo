from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.models.cliente_dv_model import ClienteDeliveryModel
from app.api.delivery.repositories.repo_endereco_dv import EnderecoRepository
from app.api.delivery.schemas.schema_endereco_dv import EnderecoOut, EnderecoCreate, EnderecoUpdate

class EnderecosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnderecoRepository(db)

    def list(self, super_token: str):
        cliente_telefone = self._token_para_telefone(super_token)
        return [EnderecoOut.model_validate(x) for x in self.repo.list_by_cliente(cliente_telefone)]

    def get(self, super_token: str, end_id: int):
        cliente_telefone = self._token_para_telefone(super_token)
        return EnderecoOut.model_validate(self.repo.get_by_cliente(cliente_telefone, end_id))

    def create(self, super_token: str, payload: EnderecoCreate):
        cliente_telefone = self._token_para_telefone(super_token)
        return EnderecoOut.model_validate(self.repo.create(cliente_telefone, payload))

    def update(self, super_token: str, end_id: int, payload: EnderecoUpdate):
        cliente_telefone = self._token_para_telefone(super_token)
        return EnderecoOut.model_validate(self.repo.update(cliente_telefone, end_id, payload))

    def delete(self, super_token: str, end_id: int):
        cliente_telefone = self._token_para_telefone(super_token)
        self.repo.delete(cliente_telefone, end_id)

    def set_padrao(self, super_token: str, end_id: int):
        cliente_telefone = self._token_para_telefone(super_token)
        return EnderecoOut.model_validate(self.repo.set_padrao(cliente_telefone, end_id))

    def _token_para_telefone(self, super_token: str) -> str:
        from app.database.db_connection import get_db
        db = self.db
        cliente = db.query(ClienteDeliveryModel).filter_by(super_token=super_token).first()
        if not cliente:
            raise HTTPException(status_code=401, detail="Token inválido")
        return cliente.telefone
