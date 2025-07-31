# app/api/pdv/repositories/meiospgto_repo.py

from typing    import List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.meiospgto_pdv    import MeiosPgtoPDVModel
from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_resumo_geral(self, data_inicio, data_fim):
        """
        Retorna lista de dicts com:
          - tipo
          - descricao
          - valor_total  (soma de movm_valor para cada tipo)
        """
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codmeiopgto.label("tipo"),
                func.max(MeiosPgtoPDVModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPDVModel,
                MovMeioPgtoPDVModel.movm_codmeiopgto == MeiosPgtoPDVModel.mpgt_codigo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',  # só pagamentos normais
            )
            .group_by(MovMeioPgtoPDVModel.movm_codmeiopgto)
            .all()
        )

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        """
        Retorna lista de dicts com:
          - empresa
          - tipo
          - descricao
          - valor_total
        """
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MovMeioPgtoPDVModel.movm_codmeiopgto.label("tipo"),
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
                MovMeioPgtoPDVModel.movm_situacao == 'N',  # idem
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MovMeioPgtoPDVModel.movm_codmeiopgto,
            )
            .all()
        )
