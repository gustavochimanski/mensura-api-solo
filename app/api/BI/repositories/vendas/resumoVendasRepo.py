# app/repositories/vendaDetalhadaRepository.py

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from app.api.pdv.models.lctoprodutos_pdv_model import LctoProdutosPDV
from app.api.BI.schemas.vendas.resumoVendas import TotaisPorEmpresa
from app.api.public.models.empresa.empresasModel import Empresa


def resumoDeVendasRepository(db: Session, vendas_request) -> list[TotaisPorEmpresa]:
    query = (
        db.query(
            LctoProdutosPDV.lcpr_codempresa.label("lcpr_codempresa"),
            Empresa.empr_nomereduzido.label("empr_nomereduzido"),    # ← aqui
            func.count(distinct(LctoProdutosPDV.lcpr_cupom)).label("total_cupons"),
            func.sum(LctoProdutosPDV.lcpr_totalprodutos).label("total_vendas"),
            func.avg(LctoProdutosPDV.lcpr_totalprodutos).label("ticket_medio"),
        )
        .join(
            Empresa,
            Empresa.empr_codigo == LctoProdutosPDV.lcpr_codempresa
        )
        .filter(
            LctoProdutosPDV.lcpr_datamvto.between(
                vendas_request.dataInicio,
                vendas_request.dataFinal
            ),
            LctoProdutosPDV.lcpr_codempresa.in_(vendas_request.empresas),
            LctoProdutosPDV.lcpr_situacao == 'N'
        )
    )

    if vendas_request.situacao:
        query = query.filter(LctoProdutosPDV.lcpr_situacao == vendas_request.situacao)
    if vendas_request.status_venda:
        query = query.filter(LctoProdutosPDV.lcpr_statusvenda == vendas_request.status_venda)
    if vendas_request.cod_vendedor:
        query = query.filter(LctoProdutosPDV.lcpr_codvendedor == vendas_request.cod_vendedor)

    # agrupar também pelo nome reduzido
    query = query.group_by(
        LctoProdutosPDV.lcpr_codempresa,
        Empresa.empr_nomereduzido
    )

    return [
        TotaisPorEmpresa(
            lcpr_codempresa=row.lcpr_codempresa,
            empr_nomereduzido=row.empr_nomereduzido,    # ← preenche aqui
            total_cupons=row.total_cupons or 0,
            total_vendas=float(row.total_vendas or 0),
            ticket_medio=float(row.ticket_medio or 0),
        )
        for row in query.all()
    ]
