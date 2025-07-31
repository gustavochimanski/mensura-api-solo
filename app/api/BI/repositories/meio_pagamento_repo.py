# app/api/pdv/repositories/meiospgto_repo.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.pdv.models.meio_pagamento.meiospgto_pdv import MeiosPgtoPDVModel
from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel


class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def listar_meios_pagamento(self):
        return self.db.query(MeiosPgtoPDVModel).all()

    def resumo_por_tipo(self, empresas: list[str], data_inicio, data_fim):
        return (
            self.db.query(
                MovMeioPgtoPDVModel.movm_codmeiopgto.label("tipo"),
                func.sum(MovMeioPgtoPDVModel.movm_valor).label("valorTotal"),
            )
            .filter(
                MovMeioPgtoPDVModel.movm_codempresa.in_(empresas),
                MovMeioPgtoPDVModel.movm_datamvto.between(data_inicio, data_fim),
            )
            .group_by(MovMeioPgtoPDVModel.movm_codmeiopgto)
            .all()
        )
