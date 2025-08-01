from typing import List
from decimal import Decimal
from sqlalchemy import func, cast, String
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel
from app.api.public.models.meiospgto_public import MeiosPgtoPublicModel


# Mapeamento código PDV (inteiro) → tipo (letra)
CODIGO_PDV_TO_TIPO = {
    "01": "N",  # Dinheiro
    "02": "H",  # Cheque
    "03": "H",  # Cheque Pré
    "04": "C",  # Convênio
    "05": "I",  # Cartão Off-line / PIX
    "06": "D",  # Cartão débito/crédito
    "07": "V",  # Ticket
    "08": "N",  # Contra Vale
    "09": "X",  # PIX
}

TIPOS_VALIDOS = {"N", "H", "C", "D", "R", "V", "I", "E", "X"}


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def _filtrar_e_validar(self, resultados):
        """
        Filtra os registros cuja tradução de tipo PDV corresponde ao tipo do Public.
        """
        filtrados = []
        for r in resultados:
            tipo_pdv = str(r.tipo).zfill(2)
            tipo_traduzido = CODIGO_PDV_TO_TIPO.get(tipo_pdv)
            if tipo_traduzido and tipo_traduzido == r.tipo_public and tipo_traduzido in TIPOS_VALIDOS:
                filtrados.append(r)
        return filtrados

    def get_resumo_geral(self, data_inicio, data_fim):
        resultados = (
            self.db.query(
                MovMeioPgtoPDVModel.movm_tipo.label("tipo"),  # ex: 01
                MeiosPgtoPublicModel.mpgt_tpmeiopgto.label("tipo_public"),  # ex: "N"
                func.max(MeiosPgtoPublicModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPublicModel,
                MovMeioPgtoPDVModel.movm_codmeiopgto == MeiosPgtoPublicModel.mpgt_codigo
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N'
            )
            .group_by(MovMeioPgtoPDVModel.movm_tipo, MeiosPgtoPublicModel.mpgt_tpmeiopgto)
            .all()
        )

        return self._filtrar_e_validar(resultados)

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        resultados = (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MovMeioPgtoPDVModel.movm_tipo.label("tipo"),  # ex: 01
                MeiosPgtoPublicModel.mpgt_tpmeiopgto.label("tipo_public"),  # ex: "N"
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
                MovMeioPgtoPDVModel.movm_situacao == 'N'
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MovMeioPgtoPDVModel.movm_tipo,
                MeiosPgtoPublicModel.mpgt_tpmeiopgto,
            )
            .all()
        )

        return self._filtrar_e_validar(resultados)
