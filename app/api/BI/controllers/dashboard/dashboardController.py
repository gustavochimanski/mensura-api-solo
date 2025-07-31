from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.BI.schemas.vendas.resumoVendas import TypeVendasPeriodoGeral
from app.database.db_connection import get_db

from app.api.BI.schemas.metas_types import TypeConsultaMetaRequest
from app.api.BI.schemas.compras_types import ConsultaMovimentoCompraRequest
from app.api.BI.schemas.dashboard_types import TypeRelacao, TypeDashboardResponse, TypeDashboardRequest
from app.api.BI.schemas.vendas.vendasPorHoraTypes import TypeVendaPorHoraRequest

from app.api.BI.controllers.vendas.vendaDetalhadaController import consultaVendaDetalhadaController

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
    vendaPorHora = consultaVendaPorHoraService(db, TypeVendaPorHoraRequest(
        dataInicio=request.dataInicio,
        dataFinal=request.dataFinal,
        empresas=empresas_str,
    ))
    # 1) Consulta relatorios
    vendas_req = TypeVendasPeriodoGeral.model_validate(
        request.model_dump() | {"empresas": empresas_str}
    )

    resumoVendas = resumoDeVendasService(vendas_req, db)
    if resumoVendas is None:
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
    total_vendas = resumoVendas.total_geral.total_vendas
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

    vendaDetalhada = consultaVendaDetalhadaController(request, db)
    compraDetalhada = compraDetalhadaService(db, compras_req)
    # 5) Retorno
    return TypeDashboardResponse(
        totais_por_empresa=resumoVendas.totais_por_empresa,
        total_geral=resumoVendas.total_geral,
        relacao=relacao,
        metas=metas,
        compras=compras,
        vendaDetalhada=vendaDetalhada,
        compraDetalhada=compraDetalhada,
        vendaPorHora=vendaPorHora,
    )
