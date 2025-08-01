from typing import List
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.meiospgto_pdv import MeiosPgtoPDVModel
from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_resumo_geral(self, data_inicio, data_fim):
        """
        Retorna um resumo geral dos meios de pagamento, agrupados por tipo (letra),
        com base na tabela pdv.meiospgto_pdv.
        """
        query = (
            self.db.query(
                MeiosPgtoPDVModel.mpgt_tipo.label("tipo"),
                func.max(MeiosPgtoPDVModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPDVModel,
                MovMeioPgtoPDVModel.movm_codmeiopgto == MeiosPgtoPDVModel.mpgt_codigo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N'
            )
            .group_by(MeiosPgtoPDVModel.mpgt_tipo)
        )

        return query.all()

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        """
        Retorna o resumo de meios de pagamento por empresa, agrupado por tipo (letra).
        As informações vêm diretamente da tabela pdv.meiospgto_pdv.
        """
        query = (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MeiosPgtoPDVModel.mpgt_tipo.label("tipo"),
                func.max(MeiosPgtoPDVModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPDVModel,
                MovMeioPgtoPDVModel.movm_codmeiopgto == MeiosPgtoPDVModel.mpgt_codigo
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
