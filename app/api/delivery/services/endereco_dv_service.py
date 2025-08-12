# --- Service ---
from sqlalchemy.orm import Session

from app.api.delivery.repositories.repo_endereco_dv import EnderecoRepository
from app.api.delivery.schemas.endereco_dv_schema import EnderecoOut, EnderecoCreate, EnderecoUpdate


class EnderecosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnderecoRepository(db)

    def list(self, cliente_id: int):
        return [EnderecoOut.model_validate(x) for x in self.repo.list_by_cliente(cliente_id)]

    def get(self, end_id: int):
        return EnderecoOut.model_validate(self.repo.get(end_id))

    def create(self, payload: EnderecoCreate):
        return EnderecoOut.model_validate(self.repo.create(payload))

    def update(self, end_id: int, payload: EnderecoUpdate):
        return EnderecoOut.model_validate(self.repo.update(end_id, payload))

    def delete(self, end_id: int):
        self.repo.delete(end_id)

    def set_padrao(self, cliente_id: int, end_id: int):
        return EnderecoOut.model_validate(self.repo.set_padrao(cliente_id, end_id))