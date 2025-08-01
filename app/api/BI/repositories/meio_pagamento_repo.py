from typing import List
from decimal import Decimal
from sqlalchemy import func, String, cast
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.meiospgto_pdv import MeiosPgtoPDVModel
from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db


    def get_resumo_geral(self, data_inicio, data_fim):
        query = (
            self.db.query(
                MeiosPgtoPDVModel.mpgt_tipo.label("tipo"),
                func.max(MeiosPgtoPDVModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPDVModel,
                func.lpad(cast(MovMeioPgtoPDVModel.movm_tipo, String), 2, '0') == MeiosPgtoPDVModel.mpgt_tipo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N'
            )
            .group_by(MeiosPgtoPDVModel.mpgt_tipo)
        )

        return query.all()

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        query = (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MeiosPgtoPDVModel.mpgt_tipo.label("tipo"),
                func.max(MeiosPgtoPDVModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPDVModel,
                func.lpad(cast(MovMeioPgtoPDVModel.movm_tipo, String), 2, '0') == MeiosPgtoPDVModel.mpgt_tipo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_codempresa.in_(empresas),
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N'
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MeiosPgtoPDVModel.mpgt_tipo
            )
        )

        return query.all()

