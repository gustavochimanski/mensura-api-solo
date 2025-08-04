from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.BI.services.departamentos_service import DepartamentosPublicService
from app.api.BI.services.meio_pagamento_service import  MeioPagamentoPDVService
from app.database.db_connection import get_db

from app.api.BI.schemas.metas_types import TypeConsultaMetaRequest
from app.api.BI.schemas.compras_types import ConsultaMovimentoCompraRequest
from app.api.BI.schemas.dashboard_types import TypeRelacao, TypeDashboardResponse, TypeDashboardRequest

from app.api.BI.services.vendas.vendaDetalhadaService import consultaVendaDetalhadaGeralService
from app.api.public.repositories.empresas.consultaEmpresas import EmpresasRepository

from app.api.BI.services.compras.compraDetalhadaByDayService import compraDetalhadaService
from app.api.BI.services.compras.resumoDeCompras import calcular_movimento_multi
from app.api.BI.services.vendas.resumoVendasService import resumoDeVendasService
from app.api.BI.services.metas.consultaMetasService import consultar_metas_periodo
from app.api.BI.services.vendas.vendaPorHoraService import consultaVendaPorHoraService
from app.utils.empresas_utils import normalizar_empresas
from app.utils.logger import logger

router = APIRouter(tags=["Dashboard"])

@router.post("/dashboard/periodo", summary="Dados Dashboard geral")
def dashboardController(
    request: TypeDashboardRequest,
    db: Session = Depends(get_db)
):
    logger.info(f"Request recebido:"
                f"inicio={request.dataInicio}, fim={request.dataFinal}")

    # Define as empresas
    repo = EmpresasRepository(db)
    empresas_str = normalizar_empresas(request.empresas, repo.buscar_codigos_ativos)

    # Chama o service corretamente
    vendaPorHora = consultaVendaPorHoraService(db, TypeDashboardRequest(
        dataInicio=request.dataInicio,
        dataFinal=request.dataFinal,
        empresas=empresas_str,
    ))
    # 1) Consulta relatorios
    vendas_req = TypeDashboardRequest.model_validate(
        request.model_dump() | {"empresas": empresas_str}
    )

    resumo_vendas = resumoDeVendasService(vendas_req, db)
    if resumo_vendas is None:
        raise HTTPException(status_code=500, detail="Erro ao consultar relatorios.")

    # 2) Consulta metas
    metas_req = TypeConsultaMetaRequest(
        dataInicio=request.dataInicio,
        dataFinal=request.dataFinal,
        empresas=empresas_str
    )
    metas = consultar_metas_periodo(metas_req, db)
    if metas is None:
        raise HTTPException(status_code=500, detail="Erro ao consultar metas.")

    # 3) Consulta compras
    compras_req = ConsultaMovimentoCompraRequest(
        dataInicio=request.dataInicio,
        dataFinal=request.dataFinal,
        empresas=empresas_str
    )
    compras = calcular_movimento_multi(db, compras_req)

    # 4) Margem bruta: quanto sobrou das relatorios
    total_vendas = resumo_vendas.total_geral.total_vendas
    total_compras = compras.total_geral

    if total_vendas > 0:
        lucro_bruto = total_vendas - total_compras
        margem_bruta_percentual = (lucro_bruto / total_vendas) * 100

        relacao = TypeRelacao(
            relacaoValue=lucro_bruto,
            relacaoPorcentagem=margem_bruta_percentual
        )
    else:
        relacao = TypeRelacao(
            relacaoValue=0.0,
            relacaoPorcentagem=0.0
        )

    venda_detalhada = consultaVendaDetalhadaGeralService(request, db)
    compra_detalhada = compraDetalhadaService(db, compras_req)

    meios_pagamento = MeioPagamentoPDVService(db).consulta_meios_pagamento_dashboard(
        empresas=empresas_str,
        data_inicio=request.dataInicio,
        data_fim=request.dataFinal,
    )

    ano_mes = datetime.strptime(request.dataInicio, "%Y-%m-%d").strftime("%Y%m")
    departamentos = DepartamentosPublicService(db).get_mais_vendidos(ano_mes

    # 5) Retorno
    return TypeDashboardResponse(
        totais_por_empresa=resumo_vendas.totais_por_empresa,
        total_geral=resumo_vendas.total_geral,
        periodo_anterior=resumo_vendas.periodo_anterior,
        relacao=relacao,
        metas=metas,
        compras=compras,
        vendaDetalhada=venda_detalhada,
        compraDetalhada=compra_detalhada,
        vendaPorHora=vendaPorHora,
        meios_pagamento=meios_pagamento,
        departamentos=departamentos
    )
