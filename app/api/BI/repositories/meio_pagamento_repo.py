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
        # Agrupar os tipos manualmente por movm_tipo → letra
        CASE_TIPO = func.case(
            value=MovMeioPgtoPDVModel.movm_tipo,
            whens={
                1: 'N',  # Dinheiro
                2: 'H',  # Cheque
                3: 'H',  # Cheque Pré
                4: 'C',  # Convênio
                5: 'I',  # Cartão Off-line
                6: 'D',  # Cartão Débito/Crédito
                7: 'V',  # Ticket
                8: 'N',  # Contra Vale
                9: 'X',  # Pix
            },
            else_='?'  # caso algum tipo esteja fora da regra
        ).label("tipo")

        query = (
            self.db.query(
                CASE_TIPO,
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
            .group_by(CASE_TIPO)
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
