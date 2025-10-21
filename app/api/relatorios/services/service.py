from __future__ import annotations

from datetime import date, datetime

from fastapi import HTTPException, status

from app.api.relatorios.repositories.repository import RelatorioRepository

class RelatoriosService:
    def __init__(self, repository: RelatorioRepository) -> None:
        self.repository = repository

    def _validar_data(self, data_str: str) -> date:
        try:
            return datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Formato de data inválido. Utilize YYYY-MM-DD.",
            ) from exc

    def relatorio_panoramico_dia(self, empresa_id: int, data: str) -> dict:
        dia = self._validar_data(data)
        return self.repository.obter_panoramico_diario(empresa_id, dia)

