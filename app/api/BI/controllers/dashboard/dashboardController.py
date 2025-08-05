from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.BI.schemas.dashboard_types import (
    TypeRelacao,
    TypeRelacaoEmpresa,
    TypeDashboardResponse,
    TypeDashboardRequest,
)
from app.api.BI.schemas.compras_types import ConsultaMovimentoCompraRequest
from app.api.BI.services.vendas.vendaDetalhadaService import consultaVendaDetalhadaGeralService
from app.api.BI.services.compras.compraDetalhadaByDayService import compraDetalhadaService
from app.api.BI.services.compras.resumoDeCompras import calcular_movimento_multi
from app.api.BI.services.vendas.resumoVendasService import resumoDeVendasService
from app.api.BI.services.metas.consultaMetasService import consultar_metas_periodo
from app.api.BI.services.vendas.vendaPorHoraService import consultaVendaPorHoraService
from app.api.BI.services.departamentos_service import DepartamentosPublicService
from app.api.BI.services.meio_pagamento_service import MeioPagamentoPDVService
from app.api.public.repositories.empresas.consultaEmpresas import EmpresasRepository
from app.database.db_connection import get_db
from app.utils.empresas_utils import normalizar_empresas
from app.utils.logger import logger

router = APIRouter(tags=["Dashboard"])

@router.post("/dashboard/periodo", summary="Dados Dashboard geral")
def dashboardController(
    request: TypeDashboardRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"Request recebido: inicio={request.dataInicio}, fim={request.dataFinal}")

    # Define as empresas
    repo = EmpresasRepository(db)
    empresas_str = normalizar_empresas(request.empresas, repo.buscar_codigos_ativos)

    # Vendas por hora
    vendaPorHora = consultaVendaPorHoraService(
        db,
        TypeDashboardRequest(
            dataInicio=request.dataInicio,
            dataFinal=request.dataFinal,
            empresas=empresas_str,
        ),
    )

    # Resumo de vendas
    vendas_req = TypeDashboardRequest.model_validate(
        request.model_dump() | {"empresas": empresas_str}
    )
    resumo_vendas = resumoDeVendasService(vendas_req, db)
    if resumo_vendas is None:
        raise HTTPException(status_code=500, detail="Erro ao consultar relatórios.")

    # Metas
    metas_req = TypeDashboardRequest.model_validate(
        {"empresas": empresas_str, "dataInicio": request.dataInicio, "dataFinal": request.dataFinal}
    )
    metas = consultar_metas_periodo(metas_req, db)
    if metas is None:
        raise HTTPException(status_code=500, detail="Erro ao consultar metas.")

    # Compras
    compras_req = ConsultaMovimentoCompraRequest(
        dataInicio=request.dataInicio,
        dataFinal=request.dataFinal,
        empresas=empresas_str
    )
    compras = calcular_movimento_multi(db, compras_req)

    # Margem bruta geral (com totais)
    total_vendas = resumo_vendas.total_geral.total_vendas
    total_compras = compras.total_geral
    if total_vendas > 0:
        lucro_bruto = total_vendas - total_compras
        margem_bruta_percentual = (lucro_bruto / total_vendas) * 100
    else:
        lucro_bruto = 0.0
        margem_bruta_percentual = 0.0

    relacao = TypeRelacao(
        total_vendas=total_vendas,
        total_compras=total_compras,
        relacaoValue=lucro_bruto,
        relacaoPorcentagem=margem_bruta_percentual
    )

    # Margem bruta por empresa
    relacao_por_empresa: list[TypeRelacaoEmpresa] = []
    for tot in resumo_vendas.totais_por_empresa:
        venda = tot.total_vendas
        compra = next(
            (c.valorTotal for c in compras.por_empresa if c.empresa == tot.lcpr_codempresa),
            0.0
        )
        if venda > 0:
            lucro = venda - compra
            perc = (lucro / venda) * 100
        else:
            lucro = 0.0
            perc = 0.0

        relacao_por_empresa.append(
            TypeRelacaoEmpresa(
                empresa=tot.lcpr_codempresa,
                total_vendas=venda,
                total_compras=1000000,
                relacaoValue=lucro,
                relacaoPorcentagem=perc
            )
        )

    # Detalhes, meios de pagamento e departamentos
    venda_detalhada = consultaVendaDetalhadaGeralService(request, db)
    compra_detalhada = compraDetalhadaService(db, compras_req)
    meios_pagamento = MeioPagamentoPDVService(db).consulta_meios_pagamento_dashboard(
        empresas=empresas_str,
        data_inicio=request.dataInicio,
        data_fim=request.dataFinal,
    )
    departamento_service = DepartamentosPublicService(db)
    departamento_geral = departamento_service.get_mais_vendidos_geral(
        data_inicio=request.dataInicio,
        data_fim=request.dataFinal,
    )
    departamento_empresa = departamento_service.get_mais_vendidos(
        data_inicio=request.dataInicio,
        data_fim=request.dataFinal,
    )

    # Retorno com relacao e relacao_por_empresa ajustados
    return TypeDashboardResponse(
        totais_por_empresa=resumo_vendas.totais_por_empresa,
        total_geral=resumo_vendas.total_geral,
        periodo_anterior=resumo_vendas.periodo_anterior,
        relacao=relacao,
        relacao_por_empresa=relacao_por_empresa,
        metas=metas,
        compras=compras,
        vendaDetalhada=venda_detalhada,
        compraDetalhada=compra_detalhada,
        vendaPorHora=vendaPorHora,
        meios_pagamento=meios_pagamento,
        departamento_geral=departamento_geral,
        departamento_empresa=departamento_empresa
    )
