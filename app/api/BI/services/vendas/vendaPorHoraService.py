from collections import defaultdict
from sqlalchemy.orm import Session
from app.api.BI.repositories.vendas.vendaPorHoraRepository import consultaVendaPorHoraRepository
from app.api.BI.schemas.dashboard_types import TypeDashboardRequest
from app.api.BI.schemas.vendas.vendasPorHoraTypes import (
    TypeVendaPorHora,
    TypeVendaPorHoraResponse,
)

def consultaVendaPorHoraService(
    db: Session,
    request: TypeDashboardRequest
) -> list[TypeVendaPorHoraResponse]:
    """
    Retorna somente os dados por empresa, por hora.
    """
    dados = consultaVendaPorHoraRepository(
        db=db,
        dataInicio=request.dataInicio,
        dataFinal=request.dataFinal,
        empresas=request.empresas,
        status_venda=request.status_venda,
        situacao=request.situacao
    )

    agrupado = defaultdict(list)

    for row in dados:
        hora = int(row.hora)
        total = float(row.total_vendas or 0)
        cupons = int(row.total_cupons or 0)
        ticket = float(row.ticket_medio or 0)

        agrupado[row.empresa].append(TypeVendaPorHora(
            hora=hora,
            total_cupons=cupons,
            total_vendas=total,
            ticket_medio=ticket
        ))

    return [
        TypeVendaPorHoraResponse(
            empresa=empresa,
            vendasPorHora=vendas
        )
        for empresa, vendas in agrupado.items()
    ]
