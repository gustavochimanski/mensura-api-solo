from typing import List
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.public.models.meiospagamento import MeiosPgtoPublicModel
from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_resumo_geral(self, data_inicio, data_fim):
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codmeiopgto.label("tipo"),
                func.max(MeiosPgtoPublicModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPublicModel,
                MovMeioPgtoPDVModel.movm_codmeiopgto == MeiosPgtoPublicModel.mpgt_codigo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
                MovMeioPgtoPDVModel.movm_valor <= Decimal("9999.99"),
            )
            .group_by(MovMeioPgtoPDVModel.movm_codmeiopgto)
            .all()
        )

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MovMeioPgtoPDVModel.movm_codmeiopgto.label("tipo"),
                func.max(MeiosPgtoPublicModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPublicModel,
                MovMeioPgtoPDVModel.movm_codmeiopgto == MeiosPgtoPublicModel.mpgt_codigo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_codempresa.in_(empresas),
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
                MovMeioPgtoPDVModel.movm_valor <= Decimal("9999.99"),
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MovMeioPgtoPDVModel.movm_codmeiopgto,
            )
            .all()
        )
