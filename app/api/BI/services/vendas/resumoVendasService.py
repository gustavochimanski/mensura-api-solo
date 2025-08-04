from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.api.BI.repositories.vendas.resumoVendasRepo import ResumoDeVendasRepository
from app.api.BI.schemas.dashboard_types import TypeDashboardRequest
from app.api.BI.schemas.vendas.resumoVendas import (
    TypeResumoVendasResponse,
    TotaisGerais,
    TotaisPorEmpresa,
)

def resumoDeVendasService(
    vendas_request: TypeDashboardRequest,
    db: Session
) -> TypeResumoVendasResponse | None:
    try:
        repo = ResumoDeVendasRepository(db)

        # período atual
        totais_por_empresa: list[TotaisPorEmpresa] = repo.resumo_venda_periodo(vendas_request)

        # período anterior
        dt_inicio_atual = datetime.strptime(vendas_request.dataInicio, "%Y-%m-%d").date()
        dt_fim_atual = datetime.strptime(vendas_request.dataFinal, "%Y-%m-%d").date()
        delta = dt_fim_atual - dt_inicio_atual

        vendas_request_anterior = TypeDashboardRequest(
            empresas=vendas_request.empresas,
            dataInicio=(dt_inicio_atual - delta - timedelta(days=1)).strftime("%Y-%m-%d"),
            dataFinal=(dt_inicio_atual - timedelta(days=1)).strftime("%Y-%m-%d"),
            situacao=vendas_request.situacao,
            status_venda=vendas_request.status_venda,
            cod_vendedor=vendas_request.cod_vendedor
        )

        comparativo = repo.resumo_venda_compara_periodo(
            vendas_request_atual=vendas_request,
            vendas_request_anterior=vendas_request_anterior
        )

        total_geral = TotaisGerais(
            total_cupons=sum(emp.total_cupons for emp in totais_por_empresa),
            total_vendas=sum(emp.total_vendas for emp in totais_por_empresa),
            ticket_medio=(
                sum(emp.ticket_medio for emp in totais_por_empresa) / len(totais_por_empresa)
                if totais_por_empresa else 0
            )
        )

        return TypeResumoVendasResponse(
            totais_por_empresa=totais_por_empresa,
            total_geral=total_geral,
            periodo_anterior=comparativo["anterior"]
        )

    except Exception as e:
        db.rollback()
        print(f"Erro no service de resumo de vendas: {e}")
        return None
