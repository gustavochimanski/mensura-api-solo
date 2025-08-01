from typing import List
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel

# mapeamento movm_tipo → letra e descrição
TIPOS_MAP = {
    1: ("N", "Dinheiro"),
    2: ("H", "Cheque à vista"),
    3: ("H", "Cheque pré"),
    4: ("C", "Convênio"),
    5: (None, None),  # Off-line (I/E) e PIX (D) serão separados abaixo
    6: (None, None),  # Débito (D) e Crédito (R)
    7: ("V", "Vale"),
    8: ("N", "Contra-Vale"),
    9: ("X", "Outro"),
}

# para os movm_tipo que têm mais de um tipo_letra, vamos criar casos específicos:
LETRA_CASE = case(
    [
        # código 5: off-line = I ou E, PIX = D
        (MovMeioPgtoPDVModel.movm_tipo == 5,
         case(
             [
                 (MovMeioPgtoPDVModel.movm_meiopagamento == 5, 'I'),  # troque aqui pela sua coluna/condição real de off-line
                 # (outra condição para 'E'),
                 # (outra condição para 'D'),
             ], else_='D'
         )
        ),
        # código 6: débito = D, crédito = R
        (MovMeioPgtoPDVModel.movm_tipo == 6,
         case(
             [(MovMeioPgtoPDVModel.movm_meiopagamento == 6, 'D')],
             else_='R'
         )
        ),
        # tipos 1,2,3,4,7,8,9 – mapeio direto
        *((MovMeioPgtoPDVModel.movm_tipo == k, v[0]) for k, v in TIPOS_MAP.items() if v[0]),
    ],
    else_='?'
).label("tipo_letra")

DESC_CASE = case(
    [
        *((MovMeioPgtoPDVModel.movm_tipo == k, v[1]) for k, v in TIPOS_MAP.items() if v[1]),
        # para 5 e 6, agrupo juntos numa descrição genérica – ajuste se precisar algo mais refinado
        (MovMeioPgtoPDVModel.movm_tipo == 5, "Off-line / PIX"),
        (MovMeioPgtoPDVModel.movm_tipo == 6, "Cartão"),
    ],
    else_="Desconhecido"
).label("descricao")


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_resumo_geral(self, data_inicio, data_fim):
        return (
            self.db
            .query(
                MovMeioPgtoPDVModel.movm_tipo.label("tipo"),
                LETRA_CASE,
                DESC_CASE,
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
                MovMeioPgtoPDVModel.movm_tipo.in_(list(TIPOS_MAP.keys()))
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_tipo,
                LETRA_CASE,
                DESC_CASE
            )
            .all()
        )

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        return (
            self.db
            .query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MovMeioPgtoPDVModel.movm_tipo.label("tipo"),
                LETRA_CASE,
                DESC_CASE,
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .filter(
                MovMeioPgtoPDVModel.movm_codempresa.in_(empresas),
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
                MovMeioPgtoPDVModel.movm_tipo.in_(list(TIPOS_MAP.keys()))
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MovMeioPgtoPDVModel.movm_tipo,
                LETRA_CASE,
                DESC_CASE
            )
            .all()
        )
