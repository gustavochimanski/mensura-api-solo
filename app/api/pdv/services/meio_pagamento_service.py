from datetime import datetime
from sqlalchemy.orm import Session

from app.api.BI.repositories.meio_pagamento_repo import MeioPagamentoRepository
from app.api.BI.schemas.meio_pagamento_types import MeioPagamentoResumoResponse, MeioPagamentoResponseFinal, \
    MeioPagamentoPorEmpresa


class MeioPagamentoPDVService:
    def __init__(self, db: Session):
        self.db = db

    def consulta_meios_pagamento_dashboard(
        self,
        empresas: list[str],
        data_inicio: str,
        data_fim: str,
    ) -> MeioPagamentoResponseFinal:
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        repo = MeioPagamentoRepository(self.db)

        # 🔹 Total geral
        geral_raw = repo.get_resumo_geral(dt_inicio, dt_fim)

        total_geral = [
            MeioPagamentoResumoResponse(
                tipo=row.tipo or "??",
                descricao=row.descricao or "DESCONHECIDO",
                valor_total=float(row.valorTotal or 0),
            )
            for row in geral_raw
        ]

        # 🔹 Por empresa
        por_empresa_raw = repo.get_resumo_por_empresa(empresas, dt_inicio, dt_fim)
        agrupado = {}

        for row in por_empresa_raw:
            cod = str(row.empresa)
            if cod not in agrupado:
                agrupado[cod] = []

            agrupado[cod].append(
                MeioPagamentoResumoResponse(
                    tipo=row.tipo or "??",
                    descricao=row.descricao or "DESCONHECIDO",
                    valor_total=float(row.valorTotal or 0),
                )
            )

        por_empresa = [
            MeioPagamentoPorEmpresa(empresa=emp, meios=meios)
            for emp, meios in agrupado.items()
        ]

        return MeioPagamentoResponseFinal(
            total_geral=total_geral,
            por_empresa=por_empresa
        )
