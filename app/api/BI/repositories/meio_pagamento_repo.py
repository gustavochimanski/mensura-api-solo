# app/api/BI/repositories/meio_pagamento_repo.py
from typing import List
from sqlalchemy import (
    select, func, cast, Integer, Table, MetaData
)
from sqlalchemy.orm import Session
from app.database.db_connection import engine
from app.api.pdv.models.meio_pagamento.movmeiopgto_pdv import MovMeioPgtoPDVModel
from app.api.public.models.meiospgto_public_model import MeiosPgtoPublicModel

# Reflete a tabela de sangrias: pdv.sangriasd_pdv
_pdvm = MetaData(schema="pdv")
sangriasd_pdv = Table("sangriasd_pdv", _pdvm, autoload_with=engine)

class MeioPagamentoRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_resumo_por_empresa(self, empresas: List[str], data_inicio, data_fim):
        """(mantido) Resumo simples por empresa: soma valor - troco."""
        mov = MovMeioPgtoPDVModel
        mp  = MeiosPgtoPublicModel

        return (
            self.db.query(
                mov.movm_codempresa.label("empresa"),
                mov.movm_codmeiopgto.label("tipo"),
                func.max(mp.mpgt_descricao).label("descricao"),
                func.sum(mov.movm_valor - func.coalesce(mov.movm_troco, 0.0)).label("valor_total"),
            )
            .join(mp, cast(mov.movm_codmeiopgto, Integer) == mp.mpgt_codfinaliz)
            .filter(
                mov.movm_codempresa.in_(empresas),
                mov.movm_datamvto.between(data_inicio, data_fim),
                mov.movm_situacao == 'N',
            )
            .group_by(mov.movm_codempresa, mov.movm_codmeiopgto)
            .all()
        )

    def get_resumo_por_empresa_completo(self, empresas: List[str], data_inicio, data_fim):
        """
        Versão equivalente à sua SQL, mas agrupando POR EMPRESA.
        Retorna: empresa, codmeiopgto, descricao, total, retiradas, qtde
        """
        mov = MovMeioPgtoPDVModel.__table__
        mp  = MeiosPgtoPublicModel.__table__

        # subselect correlacionado: soma das sangrias por empresa + meio, no período
        retiradas_sq = (
            select(func.sum(sangriasd_pdv.c.sand_valor))
            .where(
                sangriasd_pdv.c.sand_datamvto.between(data_inicio, data_fim),
                sangriasd_pdv.c.sand_codmeiopgto == mov.c.movm_codmeiopgto,
                sangriasd_pdv.c.sand_codempresa   == mov.c.movm_codempresa,
            )
            .correlate(mov)
            .scalar_subquery()
        )

        # INNER: agrega por empresa + cod + desc + tipo (igual sua query)
        inner = (
            select(
                mov.c.movm_codempresa.label("empresa"),
                cast(mov.c.movm_codmeiopgto, Integer).label("codmeiopgto"),
                mp.c.mpgt_descricao.label("descricao"),
                func.sum(mov.c.movm_valor - func.coalesce(mov.c.movm_troco, 0.0)).label("total"),
                func.coalesce(retiradas_sq, 0.0).label("retiradas"),
                func.count().label("qtde"),
            )
            .select_from(
                mov.outerjoin(
                    mp,
                    mp.c.mpgt_codfinaliz == cast(mov.c.movm_codmeiopgto, Integer)
                )
            )
            .where(
                mov.c.movm_situacao == 'N',
                mov.c.movm_datamvto.between(data_inicio, data_fim),
                mov.c.movm_codempresa.in_(empresas),
            )
            .group_by(
                mov.c.movm_codempresa,
                mov.c.movm_codmeiopgto,
                mp.c.mpgt_descricao,
                mov.c.movm_tipo,  # mantém compatibilidade com sua SQL original
            )
        ).subquery("q")

        # OUTER: consolida por empresa + cod + desc (soma total/retiradas/qtde)
        stmt = (
            select(
                inner.c.empresa,
                inner.c.codmeiopgto,
                inner.c.descricao,
                func.sum(inner.c.total).label("total"),
                func.sum(inner.c.retiradas).label("retiradas"),
                func.sum(inner.c.qtde).label("qtde"),
            )
            .group_by(inner.c.empresa, inner.c.codmeiopgto, inner.c.descricao)
            .order_by(inner.c.empresa, inner.c.codmeiopgto)
        )

        return self.db.execute(stmt).all()
