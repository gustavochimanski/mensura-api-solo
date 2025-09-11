from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.delivery.models.model_cliente_dv import ClienteDeliveryModel
from app.api.delivery.repositories.repo_endereco import EnderecoRepository
from app.api.delivery.schemas.schema_endereco import EnderecoOut, EnderecoCreate, EnderecoUpdate

class EnderecosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnderecoRepository(db)

    def list(self, super_token: str):
        cliente_id = self._token_para_cliente_id(super_token)
        return [EnderecoOut.model_validate(x) for x in self.repo.list_by_cliente(cliente_id)]

    def get(self, super_token: str, end_id: int):
        cliente_id = self._token_para_cliente_id(super_token)
        return EnderecoOut.model_validate(self.repo.get_by_cliente(cliente_id, end_id))

    def create(self, super_token: str, payload: EnderecoCreate):
        cliente_id = self._token_para_cliente_id(super_token)
        return EnderecoOut.model_validate(self.repo.create(cliente_id, payload))

    def update(self, super_token: str, end_id: int, payload: EnderecoUpdate):
        cliente_id = self._token_para_cliente_id(super_token)
        return EnderecoOut.model_validate(self.repo.update(cliente_id, end_id, payload))

    def delete(self, super_token: str, end_id: int):
        cliente_id = self._token_para_cliente_id(super_token)
        self.repo.delete(cliente_id, end_id)

    def set_padrao(self, super_token: str, end_id: int):
        cliente_id = self._token_para_cliente_id(super_token)
        return EnderecoOut.model_validate(self.repo.set_padrao(cliente_id, end_id))

    # --- função ajustada para retornar cliente_id ---
    def _token_para_cliente_id(self, super_token: str) -> int:
        cliente = self.db.query(ClienteDeliveryModel).filter_by(super_token=super_token).first()
        if not cliente:
            raise HTTPException(status_code=401, detail="Token inválido")
        return cliente.id
