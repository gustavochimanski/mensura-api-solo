from sqlalchemy.orm import Session
from app.api.BI.schemas.metas_types import (
    TypeConsultaMetaRequest,
    TypeDashboardMetaReturn,
    TotalGeralMeta,
)
from app.api.BI.repositories.metas.metasRepo import buscar_metas_por_periodo
from app.api.BI.schemas.metas_types import TypeTotaisPorEmpresaMetaResponse


def consultar_metas_periodo(
    request: TypeConsultaMetaRequest,
    session: Session
) -> TypeDashboardMetaReturn:
    totais_por_empresa: list[TypeTotaisPorEmpresaMetaResponse] = buscar_metas_por_periodo(session, request)

    # Agrupar por tipo para gerar o total geral
    total_geral_dict = {}
    for meta in totais_por_empresa:
        if meta.tipo not in total_geral_dict:
            total_geral_dict[meta.tipo] = 0
        total_geral_dict[meta.tipo] += meta.valorMeta

    total_geral: list[TotalGeralMeta] = [
        TotalGeralMeta(tipo=tipo, valorMeta=round(valor, 2))
        for tipo, valor in total_geral_dict.items()
    ]

    return TypeDashboardMetaReturn(
        totais_por_empresa=totais_por_empresa,
        total_geral=total_geral
    )
