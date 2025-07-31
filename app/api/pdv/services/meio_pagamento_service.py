from datetime import datetime
from sqlalchemy.orm import Session

from app.api.BI.repositories.meio_pagamento_repo import MeioPagamentoRepository
from app.api.BI.schemas.dashboard_types import MeioPagamentoResumoResponse


class MeioPagamentoPDVService:
    def __init__(self, db: Session):
        self.db = db

    def consulta_meios_pagamento_dashboard(
        self,
        empresas: list[str],
        data_inicio: str,
        data_fim: str,
    ) -> list[MeioPagamentoResumoResponse]:
        # 🔁 Converte string para date
        dt_inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()

        repo = MeioPagamentoRepository(self.db)
        rows = repo.get_resumo_por_tipo(empresas, dt_inicio, dt_fim)

        return [
            MeioPagamentoResumoResponse(
                empresa=empresa,
                tipo=tipo or "??",
                descricao=descricao or "DESCONHECIDO",
                valor_total=float(valor or 0),
            )
            for empresa, tipo, descricao, valor in rows
        ]

