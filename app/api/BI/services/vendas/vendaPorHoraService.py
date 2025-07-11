from collections import defaultdict
from sqlalchemy.orm import Session
from app.api.BI.repositories.vendas.vendaPorHoraRepository import consultaVendaPorHoraRepository
from app.api.BI.schemas.vendas.vendasPorHoraTypes import (
    TypeVendaPorHoraRequest,
    TypeVendaPorHora,
    TypeVendaPorHoraResponse,
    TypeVendaPorHoraComTotalGeralResponse
)
import logging

logger = logging.getLogger(__name__)

def consultaVendaPorHoraService(
    db: Session,
    request: TypeVendaPorHoraRequest
) -> TypeVendaPorHoraComTotalGeralResponse:
    dados = consultaVendaPorHoraRepository(
        db=db,
        dataInicio=request.dataInicio,
        dataFinal=request.dataFinal,
        empresas=request.empresas,
        status_venda=request.status_venda,
        situacao=request.situacao
    )

    agrupado = defaultdict(list)
    total_por_hora = defaultdict(lambda: {
        "total_cupons": 0,
        "total_vendas": 0.0,
        "ticket_medio": 0.0,
        "qtd_empresas": 0
    })

    for row in dados:
        hora = int(row.hora)
        total = float(row.total_vendas or 0)
        cupons = int(row.total_cupons or 0)
        ticket = float(row.ticket_medio or 0)

        # Agrupa por empresa
        agrupado[row.empresa].append(TypeVendaPorHora(
            hora=hora,
            total_cupons=cupons,
            total_vendas=total,
            ticket_medio=ticket
        ))

        # Acumula totais por hora
        total_por_hora[hora]["total_cupons"] += cupons
        total_por_hora[hora]["total_vendas"] += total
        total_por_hora[hora]["ticket_medio"] += ticket
        total_por_hora[hora]["qtd_empresas"] += 1

    # Gera totais por hora (média de ticket médio por empresa)
    total_geral_por_hora = []
    for hora, dados in sorted(total_por_hora.items()):
        qtd_empresas = dados["qtd_empresas"] or 1
        ticket_medio_geral = dados["ticket_medio"] / qtd_empresas

        total_geral_por_hora.append(TypeVendaPorHora(
            hora=hora,
            total_cupons=dados["total_cupons"],
            total_vendas=dados["total_vendas"],
            ticket_medio=ticket_medio_geral
        ))

    por_empresa = [
        TypeVendaPorHoraResponse(
            empresa=empresa,
            vendasPorHora=vendas
        )
        for empresa, vendas in agrupado.items()
    ]

    return TypeVendaPorHoraComTotalGeralResponse(
        totalGeral=total_geral_por_hora,
        porEmpresa=por_empresa
    )
