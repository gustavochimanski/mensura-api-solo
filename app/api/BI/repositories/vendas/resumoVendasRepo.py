# app/repositories/vendaDetalhadaRepository.py

from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from app.api.public.models.empresa.empresasModel import Empresa
from app.api.pdv.models.lctoprodutos_pdv_model import LctoProdutosPDV
from app.api.BI.schemas.vendas.resumoVendas import TotaisPorEmpresa

def resumoDeVendasRepository(db: Session, vendas_request) -> list[TotaisPorEmpresa]:
    # 1) Monta a query incluindo o nome reduzido da empresa
    query = (
        db.query(
            LctoProdutosPDV.lcpr_codempresa.label("lcpr_codempresa"),
            Empresa.empr_nomereduzido.label("lcpr_nomereduzido"),  # usa o nome do seu model
            func.count(distinct(LctoProdutosPDV.lcpr_cupom)).label("total_cupons"),
            func.sum(LctoProdutosPDV.lcpr_totalprodutos).label("total_vendas"),
            func.avg(LctoProdutosPDV.lcpr_totalprodutos).label("ticket_medio"),
        )
        # 2) JOIN usando empr_codigo (String)
        .join(
            Empresa,
            LctoProdutosPDV.lcpr_codempresa == Empresa.empr_codigo
        )
        .filter(
            LctoProdutosPDV.lcpr_datamvto.between(
                vendas_request.dataInicio,
                vendas_request.dataFinal
            ),
            LctoProdutosPDV.lcpr_codempresa.in_(vendas_request.empresas),
            LctoProdutosPDV.lcpr_situacao == 'A'
        )
    )

    # filtros opcionais
    if vendas_request.situacao:
        query = query.filter(LctoProdutosPDV.lcpr_situacao == vendas_request.situacao)
    if vendas_request.status_venda:
        query = query.filter(LctoProdutosPDV.lcpr_statusvenda == vendas_request.status_venda)
    if vendas_request.cod_vendedor:
        query = query.filter(LctoProdutosPDV.lcpr_codvendedor == vendas_request.cod_vendedor)

    query = query.group_by(
        LctoProdutosPDV.lcpr_codempresa,
        Empresa.empr_nomereduzido
    )

    # 3) Mapeia para o schema, incluindo nomereduzido
    return [
        TotaisPorEmpresa(
            lcpr_codempresa   = row.lcpr_codempresa,
            lcpr_nomereduzido = row.lcpr_nomereduzido,
            total_cupons      = row.total_cupons or 0,
            total_vendas      = float(row.total_vendas or 0),
            ticket_medio      = float(row.ticket_medio or 0),
        )
        for row in query.all()
    ]
