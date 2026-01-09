from decimal import Decimal
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.cadastros.models.model_regiao_entrega import RegiaoEntregaModel


def _to_decimal(value: Decimal | float | int | str | None) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class RegiaoEntregaRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_empresa(self, empresa_id: int):
        return (
            self.db.query(RegiaoEntregaModel)
            .filter_by(empresa_id=empresa_id)
            .order_by(RegiaoEntregaModel.distancia_max_km.asc())
            .all()
        )

    def get(self, regiao_id: int):
        return self.db.query(RegiaoEntregaModel).filter_by(id=regiao_id).first()

    def get_by_distancia(
        self, empresa_id: int, distancia_km: Decimal | float | int | str
    ) -> Optional[RegiaoEntregaModel]:
        distancia = _to_decimal(distancia_km)
        if distancia is None:
            return None

        return (
            self.db.query(RegiaoEntregaModel)
            .filter(
                RegiaoEntregaModel.empresa_id == empresa_id,
                RegiaoEntregaModel.ativo == True,
            )
            .filter(
                # Verifica se a distância está dentro do intervalo da faixa
                RegiaoEntregaModel.distancia_min_km <= distancia,
                or_(
                    RegiaoEntregaModel.distancia_max_km.is_(None),
                    RegiaoEntregaModel.distancia_max_km >= distancia,
                )
            )
            .order_by(RegiaoEntregaModel.distancia_max_km.asc())
            .first()
        )

    def existe_faixa_sobreposta(
        self,
        *,
        empresa_id: int,
        distancia_max_km: Decimal | float | int | str | None,
        ignorar_id: Optional[int] = None,
    ) -> bool:
        distancia_max = _to_decimal(distancia_max_km)

        query = self.db.query(RegiaoEntregaModel).filter(
            RegiaoEntregaModel.empresa_id == empresa_id,
        )

        if ignorar_id is not None:
            query = query.filter(RegiaoEntregaModel.id != ignorar_id)

        if distancia_max is not None:
            query = query.filter(RegiaoEntregaModel.distancia_max_km == distancia_max)
        else:
            query = query.filter(RegiaoEntregaModel.distancia_max_km.is_(None))

        return self.db.query(query.exists()).scalar()

    def create(self, regiao: RegiaoEntregaModel):
        self.db.add(regiao)
        self.db.commit()
        self.db.refresh(regiao)
        return regiao

    def update(self, regiao: RegiaoEntregaModel, data: dict):
        for k, v in data.items():
            setattr(regiao, k, v)
        self.db.commit()
        self.db.refresh(regiao)
        return regiao

    def delete(self, regiao: RegiaoEntregaModel):
        self.db.delete(regiao)
        self.db.commit()

