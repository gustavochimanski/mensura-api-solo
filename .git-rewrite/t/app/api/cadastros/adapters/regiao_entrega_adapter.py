from typing import Optional
from decimal import Decimal
from sqlalchemy.orm import Session

from app.api.cadastros.contracts.regiao_entrega_contract import (
    IRegiaoEntregaContract,
    RegiaoEntregaDTO,
)
from app.api.cadastros.repositories.repo_regiao_entrega import RegiaoEntregaRepository
from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel


class RegiaoEntregaAdapter(IRegiaoEntregaContract):
    """Implementação do contrato de região de entrega baseada no repositório atual."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = RegiaoEntregaRepository(db)

    def _to_dto(self, r: RegiaoEntregaModel) -> RegiaoEntregaDTO:
        return RegiaoEntregaDTO(
            id=r.id,
            empresa_id=r.empresa_id,
            distancia_max_km=r.distancia_max_km,
            taxa_entrega=r.taxa_entrega,
            ativo=bool(r.ativo),
            tempo_estimado_min=getattr(r, "tempo_estimado_min", None),
        )

    def obter_regiao_por_distancia(self, empresa_id: int, distancia_km: Decimal) -> Optional[RegiaoEntregaDTO]:
        r = self.repo.get_by_distancia(empresa_id, distancia_km)
        if not r:
            return None
        return self._to_dto(r)


