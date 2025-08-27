from sqlalchemy.orm import Session
from app.api.delivery.repositories.repo_endereco_dv import EnderecoRepository
from app.api.delivery.schemas.schema_endereco_dv import EnderecoOut, EnderecoCreate, EnderecoUpdate

class EnderecosService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EnderecoRepository(db)

    def list(self, cliente_telefone: str):
        return [EnderecoOut.model_validate(x) for x in self.repo.list_by_cliente(cliente_telefone)]

    def get(self, cliente_telefone: str, end_id: int):
        return EnderecoOut.model_validate(self.repo.get_by_cliente(cliente_telefone, end_id))

    def create(self, cliente_telefone: str, payload: EnderecoCreate):
        return EnderecoOut.model_validate(self.repo.create(cliente_telefone, payload))

    def update(self, cliente_telefone: str, end_id: int, payload: EnderecoUpdate):
        return EnderecoOut.model_validate(self.repo.update(cliente_telefone, end_id, payload))

    def delete(self, cliente_telefone: str, end_id: int):
        self.repo.delete(cliente_telefone, end_id)

    def set_padrao(self, cliente_telefone: str, end_id: int):
        return EnderecoOut.model_validate(self.repo.set_padrao(cliente_telefone, end_id))
