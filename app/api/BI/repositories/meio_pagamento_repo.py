# app/api/pdv/repositories/meiospgto_repo.py

from typing import List
from sqlalchemy import func, cast, Integer
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel

from app.api.public.models.meiospgto_public_model import MeiosPgtoPublicModel  # <<< IMPORTANTE


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
                cast(MovMeioPgtoPDVModel.movm_codmeiopgto, Integer) == MeiosPgtoPublicModel.mpgt_codfinaliz
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
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
                cast(MovMeioPgtoPDVModel.movm_codmeiopgto, Integer) == MeiosPgtoPublicModel.mpgt_codfinaliz
            )
            .filter(
                MovMeioPgtoPDVModel.movm_codempresa.in_(empresas),
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MovMeioPgtoPDVModel.movm_codmeiopgto,
            )
            .all()
        )
