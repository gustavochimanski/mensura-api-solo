from typing import List
from decimal import Decimal
from sqlalchemy import func, cast, String, Integer
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel
from app.api.public.models.meiospgto_public import MeiosPgtoPublicModel


# Mapeamento de código numérico do PDV → tipo letra do Public
CODIGO_PDV_TO_TIPO = {
    "01": "N",  # Dinheiro
    "02": "H",  # Cheque
    "03": "H",  # Cheque Pré
    "04": "C",  # Convênio
    "05": "I",  # Off-line (ou E ou X → depende)
    "06": "D",  # Cartão débito/crédito
    "07": "V",  # Ticket
    "08": "N",  # Contra Vale
    "09": "X",  # Cashback (removido, mas código pode existir)
}

# Tipos válidos no public
TIPOS_VALIDOS = {"N", "H", "C", "D", "R", "V", "I", "E", "X"}


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def _filtrar_tipos_validos(self, resultados):
        """
        Mantém apenas os resultados onde o tipo numérico do PDV mapeia
        para um tipo letra válido no Public.
        """
        filtrados = []
        for r in resultados:
            tipo_letra = CODIGO_PDV_TO_TIPO.get(str(r.tipo).zfill(2))
            if tipo_letra in TIPOS_VALIDOS:
                filtrados.append(r)
        return filtrados

    def get_resumo_geral(self, data_inicio, data_fim):
        resultados = (
            self.db.query(
                MovMeioPgtoPDVModel.movm_tipo.label("tipo"),
                func.max(MeiosPgtoPublicModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPublicModel,
                CODIGO_PDV_TO_TIPO.get(cast(MovMeioPgtoPDVModel.movm_tipo, String)) ==
                cast(MeiosPgtoPublicModel.mpgt_tpmeiopgto, String)
            )
            .filter(
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
                MovMeioPgtoPDVModel.movm_valor <= Decimal("9999.99"),
            )
            .group_by(MovMeioPgtoPDVModel.movm_tipo)
            .all()
        )

        return self._filtrar_tipos_validos(resultados)

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        resultados = (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MovMeioPgtoPDVModel.movm_tipo.label("tipo"),
                func.max(MeiosPgtoPublicModel.mpgt_descricao).label("descricao"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valor_total"),
            )
            .join(
                MeiosPgtoPublicModel,
                CODIGO_PDV_TO_TIPO.get(cast(MovMeioPgtoPDVModel.movm_tipo, String)) ==
                cast(MeiosPgtoPublicModel.mpgt_tpmeiopgto, String)
            )
            .filter(
                MovMeioPgtoPDVModel.movm_codempresa.in_(empresas),
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
                MovMeioPgtoPDVModel.movm_situacao == 'N',
                MovMeioPgtoPDVModel.movm_valor <= Decimal("9999.99"),
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MovMeioPgtoPDVModel.movm_tipo,
            )
            .all()
        )

        return self._filtrar_tipos_validos(resultados)
