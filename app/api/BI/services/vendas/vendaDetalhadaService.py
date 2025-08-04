from sqlalchemy.orm import Session
from app.api.BI.repositories.vendas.vendaDetalhadaRepository import consultaVendaDetalhadaRepository
from app.api.BI.schemas.dashboard_types import TypeDashboardRequest
from app.api.BI.schemas.vendas.vendaDetalhadaTypes import (
    TypeVendaDetalhadaResponse,
    TypeVendaByDay,
    TypeVendaDetalhadaEmpresa,
)

def consultaVendaDetalhadaGeralService(
    request: TypeDashboardRequest,
    db: Session  # ✅ nome padrão, já que vem do get_db
) -> TypeVendaDetalhadaResponse:
    venda_empresas: list[TypeVendaDetalhadaEmpresa] = []

    for empresa in request.empresas:
        resultados = consultaVendaDetalhadaRepository(
            db,
            empresa,
            request.dataInicio,
            request.dataFinal
        )

        vendas_por_dia = [
            TypeVendaByDay(data=d.strftime("%Y-%m-%d"), valor=v) for d, v in resultados
        ]

        venda_empresas.append(
            TypeVendaDetalhadaEmpresa(
                empresa=empresa,
                dates=vendas_por_dia
            )
        )

    return TypeVendaDetalhadaResponse(
        dataInicio=request.dataInicio,
        dataFinal=request.dataFinal,
        vendaEmpresas=venda_empresas
    )
