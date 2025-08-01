from typing import List
from decimal import Decimal
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session

from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel
from app.api.public.models.meiospgto_public import MeiosPgtoPublicModel

# condições que mapeiam movm_tipo → mpgt_tpmeiopgto
FILTRO_TIPO = or_(
    and_(MovMeioPgtoPDVModel.movm_tipo == 1, MeiosPgtoPublicModel.mpgt_tpmeiopgto == 'N'),
    and_(MovMeioPgtoPDVModel.movm_tipo == 2, MeiosPgtoPublicModel.mpgt_tpmeiopgto == 'H'),
    and_(MovMeioPgtoPDVModel.movm_tipo == 3, MeiosPgtoPublicModel.mpgt_tpmeiopgto == 'H'),
    and_(MovMeioPgtoPDVModel.movm_tipo == 4, MeiosPgtoPublicModel.mpgt_tpmeiopgto == 'C'),
    # código 05 atende off-line (I/E) e PIX (D)
    and_(MovMeioPgtoPDVModel.movm_tipo == 5, MeiosPgtoPublicModel.mpgt_tpmeiopgto.in_(['I','E','D'])),
    # código 06 atende débito (D) e crédito (R)
    and_(MovMeioPgtoPDVModel.movm_tipo == 6, MeiosPgtoPublicModel.mpgt_tpmeiopgto.in_(['D','R'])),
    and_(MovMeioPgtoPDVModel.movm_tipo == 7, MeiosPgtoPublicModel.mpgt_tpmeiopgto == 'V'),
    and_(MovMeioPgtoPDVModel.movm_tipo == 8, MeiosPgtoPublicModel.mpgt_tpmeiopgto == 'N'),
    and_(MovMeioPgtoPDVModel.movm_tipo == 9, MeiosPgtoPublicModel.mpgt_tpmeiopgto == 'X'),
)

class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_resumo_geral(self, data_inicio, data_fim):
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_tipo.label("tipo"),
                MeiosPgtoPublicModel.mpgt_tpmeiopgto.label("tipo_letra"),
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
                FILTRO_TIPO
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_tipo,
                MeiosPgtoPublicModel.mpgt_tpmeiopgto
            )
            .all()
        )

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codempresa.label("empresa"),
                MovMeioPgtoPDVModel.movm_tipo.label("tipo"),
                MeiosPgtoPublicModel.mpgt_tpmeiopgto.label("tipo_letra"),
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
                FILTRO_TIPO
            )
            .group_by(
                MovMeioPgtoPDVModel.movm_codempresa,
                MovMeioPgtoPDVModel.movm_tipo,
                MeiosPgtoPublicModel.mpgt_tpmeiopgto,
            )
            .all()
        )
