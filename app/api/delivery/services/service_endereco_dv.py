from sqlalchemy.orm import Session
from app.api.delivery.repositories.repo_endereco_dv import EnderecoRepository
from app.api.delivery.schemas.schema_endereco_dv import EnderecoOut, EnderecoCreate, EnderecoUpdate

class EnderecosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnderecoRepository(db)

    def list(self, super_token: str):
        return [EnderecoOut.model_validate(x) for x in self.repo.list_by_cliente(super_token)]

    def get(self, super_token: str, end_id: int):
        return EnderecoOut.model_validate(self.repo.get_by_cliente(super_token, end_id))

    def create(self, super_token: str, payload: EnderecoCreate):
        return EnderecoOut.model_validate(self.repo.create(super_token, payload))

    def update(self, super_token: str, end_id: int, payload: EnderecoUpdate):
        return EnderecoOut.model_validate(self.repo.update(super_token, end_id, payload))

    def delete(self, super_token: str, end_id: int):
        self.repo.delete(super_token, end_id)

    def set_padrao(self, super_token: str, end_id: int):
        return EnderecoOut.model_validate(self.repo.set_padrao(super_token, end_id))
