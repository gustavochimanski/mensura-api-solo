from sqlalchemy.orm import Session
from app.api.BI.repositories.vendas.resumoVendasRepo import resumoDeVendasRepository
from app.api.BI.schemas.vendas.resumoVendas import (
    TypeVendasPeriodoGeral,
    TypeResumoVendasResponse,
    TotaisGerais,
    TotaisPorEmpresa,
)

def resumoDeVendasService(
    vendas_request: TypeVendasPeriodoGeral,
    db: Session  # ✅ recebe do controller via Depends(get_db)
) -> TypeResumoVendasResponse | None:
    try:
        totais_por_empresa: list[TotaisPorEmpresa] = resumoDeVendasRepository(db, vendas_request)

        total_geral = TotaisGerais(
            total_cupons=sum(emp.total_cupons for emp in totais_por_empresa),
            total_vendas=sum(emp.total_vendas for emp in totais_por_empresa),
            ticket_medio=(
                sum(emp.ticket_medio for emp in totais_por_empresa) / len(totais_por_empresa)
                if totais_por_empresa else 0
            )
        )

        return TypeResumoVendasResponse(
            empresas=vendas_request.empresas,
            dataInicio=vendas_request.dataInicio,
            dataFinal=vendas_request.dataFinal,
            totais_por_empresa=totais_por_empresa,
            total_geral=total_geral
        )

    except Exception as e:
        db.rollback()  # rollback pra manter a conexão limpa
        print(f"Erro no service de resumo de vendas: {e}")
        return None
