# app/api/pdv/repositories/meiospgto_repo.py

from typing import List
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel
from app.api.public.models.meiospgto_public import MeiosPgtoPublicModel


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_resumo_geral(self, data_inicio, data_fim):
        """
        Retorna lista de dicts com:
          - codigo    (mpgt_codigo do public)
          - descricao (mpgt_descricao do public)
          - tipo      (mpgt_tipo do public)
          - valor_total (soma de movm_valor do PDV)
        """
        return (
            self.db.query(
                MeiosPgtoPublicModel.mpgt_codigo.label("codigo"),
                MeiosPgtoPublicModel.mpgt_descricao.label("descricao"),
                MeiosPgtoPublicModel.mpgt_tipo.label("tipo"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPublicModel,
                MovMeioPgtoPDVModel.movm_codmeiopgto == MeiosPgtoPublicModel.mpgt_codigo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
            )
            # Agrupamos por código, descrição e tipo para poder usar esses campos no SELECT
            .group_by(
                MeiosPgtoPublicModel.mpgt_codigo,
                MeiosPgtoPublicModel.mpgt_descricao,
                MeiosPgtoPublicModel.mpgt_tipo,
            )
            .all()
        )

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        """
        Retorna lista de dicts com:
          - empresa   (movm_codempresa do PDV)
          - codigo    (mpgt_codigo do public)
          - descricao (mpgt_descricao do public)
          - tipo      (mpgt_tipo do public)
          - valor_total (soma de movm_valor do PDV)
        """
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MeiosPgtoPublicModel.mpgt_codigo.label("codigo"),
                MeiosPgtoPublicModel.mpgt_descricao.label("descricao"),
                MeiosPgtoPublicModel.mpgt_tipo.label("tipo"),
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
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MeiosPgtoPublicModel.mpgt_codigo,
                MeiosPgtoPublicModel.mpgt_descricao,
                MeiosPgtoPublicModel.mpgt_tipo,
            )
            .all()
        )
