from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.api.empresas.contracts.empresa_contract import (
    IEmpresaContract,
    EmpresaDTO,
)
from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.empresas.models.empresa_model import EmpresaModel


class EmpresaAdapter(IEmpresaContract):
    """Implementação do contrato de empresas baseada no repositório atual."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = EmpresaRepository(db)

    def _to_empresa_dto(self, e: EmpresaModel) -> EmpresaDTO:
        lat = float(e.latitude) if e.latitude is not None else None
        lon = float(e.longitude) if e.longitude is not None else None
        return EmpresaDTO(
            id=e.id,
            nome=e.nome,
            cnpj=e.cnpj,
            telefone=e.telefone,
            slug=getattr(e, "slug", None),
            cep=e.cep,
            logradouro=e.logradouro,
            numero=e.numero,
            bairro=e.bairro,
            cidade=e.cidade,
            estado=e.estado,
            latitude=lat,
            longitude=lon,
        )

    def obter_empresa(self, empresa_id: int) -> Optional[EmpresaDTO]:
        e = self.repo.get_empresa_by_id(empresa_id)
        if not e:
            return None
        return self._to_empresa_dto(e)

    def obter_coordenadas_empresa(self, empresa_id: int) -> Optional[Tuple[float, float]]:
        e = self.repo.get_empresa_by_id(empresa_id)
        if not e:
            return None
        lat = float(e.latitude) if e.latitude is not None else None
        lon = float(e.longitude) if e.longitude is not None else None
        if lat is None or lon is None:
            return None
        return (lat, lon)


