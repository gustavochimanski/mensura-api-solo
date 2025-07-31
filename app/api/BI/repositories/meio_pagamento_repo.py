# app/api/pdv/repositories/meiospgto_repo.py

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.pdv.models.meio_pagamento.meiospgto_pdv import MeiosPgtoPDVModel
from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, codigo: str) -> Optional[MeiosPgtoPDVModel]:
        return self.db.query(MeiosPgtoPDVModel).filter(MeiosPgtoPDVModel.mpgt_codigo == codigo).first()

    def list(self, skip: int = 0, limit: int = 100) -> List[MeiosPgtoPDVModel]:
        return self.db.query(MeiosPgtoPDVModel).offset(skip).limit(limit).all()
    def get_resumo_por_tipo(
        self,
        empresas: List[str],
        data_inicio,
        data_fim
    ) -> List[tuple]:
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codmeiopgto.label("tipo"),
                MeiosPgtoPDVModel.mpgt_descricao.label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valorTotal"),
            )
            .outerjoin(
                MeiosPgtoPDVModel,
                MovMeioPgtoPDVModel.movm_codmeiopgto == MeiosPgtoPDVModel.mpgt_codigo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_codempresa.in_(empresas),
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codmeiopgto,
                MeiosPgtoPDVModel.mpgt_descricao
            )
            .order_by(func.sum(MovMeioPgtoPDVModel.movm_valor).desc())
            .all()
        )
