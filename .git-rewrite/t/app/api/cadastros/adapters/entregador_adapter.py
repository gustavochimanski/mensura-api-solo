from typing import Optional, List
from sqlalchemy.orm import Session

from app.api.cadastros.contracts.entregador_contract import (
    IEntregadorContract,
    EntregadorDTO,
)
from app.api.cadastros.repositories.repo_entregadores import EntregadorRepository
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.cadastros.models.model_entregador_dv import EntregadorDeliveryModel


class EntregadorAdapter(IEntregadorContract):
    """Implementação do contrato de entregadores baseada nos repositórios atuais."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = EntregadorRepository(db)
        self.emp_repo = EmpresaRepository(db)

    def _to_entregador_dto(self, e: EntregadorDeliveryModel) -> EntregadorDTO:
        return EntregadorDTO(
            id=e.id,
            nome=e.nome,
            telefone=e.telefone,
        )

    def obter_entregador(self, entregador_id: int) -> Optional[EntregadorDTO]:
        e = self.repo.get(entregador_id)
        if not e:
            return None
        return self._to_entregador_dto(e)

    def listar_por_empresa(self, empresa_id: int) -> List[EntregadorDTO]:
        empresa = self.emp_repo.get_empresa_by_id(empresa_id)
        if not empresa or not getattr(empresa, "entregadores", None):
            return []
        return [self._to_entregador_dto(e) for e in empresa.entregadores]


