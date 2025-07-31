# app/repositories/vendaDetalhadaRepository.py

from sqlalchemy import func, distinct, cast, Integer
from sqlalchemy.orm import Session
from app.api.pdv.models.lctoprodutos_pdv_model import LctoProdutosPDV
from app.api.mensura.models.empresa_model       import EmpresaModel
from app.api.BI.schemas.vendas.resumoVendas    import TotaisPorEmpresa

def resumoDeVendasRepository(db: Session, vendas_request) -> list[TotaisPorEmpresa]:
    # 1) Monta a query incluindo o nome reduzido da empresa
    query = (
        db.query(
            LctoProdutosPDV.lcpr_codempresa.label("lcpr_codempresa"),
            EmpresaModel.nomereduzido.label("lcpr_nomereduzido"),
            func.count(distinct(LctoProdutosPDV.lcpr_cupom)).label("total_cupons"),
            func.sum(LctoProdutosPDV.lcpr_totalprodutos).label("total_vendas"),
            func.avg(LctoProdutosPDV.lcpr_totalprodutos).label("ticket_medio"),
        )
        # 2) JOIN — ajustar o cast se necessário para casar tipos
        .join(
            EmpresaModel,
            cast(LctoProdutosPDV.lcpr_codempresa, Integer) == EmpresaModel.id
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

    # filtros condicionais…
    if vendas_request.situacao:
        query = query.filter(LctoProdutosPDV.lcpr_situacao == vendas_request.situacao)
    if vendas_request.status_venda:
        query = query.filter(LctoProdutosPDV.lcpr_statusvenda == vendas_request.status_venda)
    if vendas_request.cod_vendedor:
        query = query.filter(LctoProdutosPDV.lcpr_codvendedor == vendas_request.cod_vendedor)

    query = query.group_by(
        LctoProdutosPDV.lcpr_codempresa,
        EmpresaModel.nomereduzido
    )

    # 3) Mapeia direto para o schema, agora incluindo nomereduzido
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
