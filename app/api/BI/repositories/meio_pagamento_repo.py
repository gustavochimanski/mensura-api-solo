from typing import List
from decimal import Decimal
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel
from app.api.public.models.meiospgto_public import MeiosPgtoPublicModel

# Mapeamento código PDV (string) → tipo (letra)
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

# Inverte mapeamento para letra → [int(códigos)]
INVERTED_MAP = {}
for code_str, letra in CODIGO_PDV_TO_TIPO.items():
    INVERTED_MAP.setdefault(letra, []).append(int(code_str))

class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_resumo_geral(self, data_inicio, data_fim):
        # Construímos uma lista de filtros do tipo:
        # (p.mpgt_tpmeiopgto == letra) AND (m.movm_tipo IN códigos_da_letra)
        filtros_por_letra = [
            and_(
                MeiosPgtoPublicModel.mpgt_tpmeiopgto == letra,
                MovMeioPgtoPDVModel.movm_tipo.in_(codigos)
            )
            for letra, codigos in INVERTED_MAP.items()
        ]

        query = (
            self.db.query(
                MeiosPgtoPublicModel.mpgt_tpmeiopgto.label("tipo"),     # ex: "N"
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
                or_(*filtros_por_letra)
            )
            .group_by(MeiosPgtoPublicModel.mpgt_tpmeiopgto)
        )

        return query.all()

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        filtros_por_letra = [
            and_(
                MeiosPgtoPublicModel.mpgt_tpmeiopgto == letra,
                MovMeioPgtoPDVModel.movm_tipo.in_(codigos)
            )
            for letra, codigos in INVERTED_MAP.items()
        ]

        query = (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MeiosPgtoPublicModel.mpgt_tpmeiopgto.label("tipo"),
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
                or_(*filtros_por_letra)
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MeiosPgtoPublicModel.mpgt_tpmeiopgto
            )
        )

        return query.all()
