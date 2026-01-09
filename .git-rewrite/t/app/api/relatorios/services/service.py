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

    def _validar_periodo(self, inicio: str, fim: str) -> tuple[date, date]:
        data_inicio = self._validar_data(inicio)
        data_fim = self._validar_data(fim)

        if data_fim < data_inicio:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Data final não pode ser anterior à data inicial.",
            )

        return data_inicio, data_fim

    def relatorio_panoramico_periodo(self, empresa_id: int, inicio: str, fim: str) -> dict:
        data_inicio, data_fim = self._validar_periodo(inicio, fim)
        return self.repository.obter_panoramico_periodo(
            empresa_id=empresa_id,
            inicio=data_inicio,
            fim=data_fim,
        )

    def relatorio_mes_anterior(self, empresa_id: int, referencia_str: str) -> dict:
        referencia = self._validar_data(referencia_str)
        return self.repository.obter_panoramico_mes_anterior(
            empresa_id=empresa_id,
            referencia=referencia,
        )

    def ranking_bairro(self, empresa_id: int, inicio: str, fim: str, limite: int = 10) -> list:
        data_inicio, data_fim = self._validar_periodo(inicio, fim)
        return self.repository.ranking_por_bairro(
            empresa_id=empresa_id,
            inicio=data_inicio,
            fim=data_fim,
            limite=limite,
        )

    def ultimos_7_dias_comparativo(self, empresa_id: int, referencia_str: str) -> dict:
        referencia = self._validar_data(referencia_str)
        return self.repository.vendas_ultimos_7_dias_comparativo(
            empresa_id=empresa_id,
            referencia=referencia,
        )

    def vendas_pico_hora(self, empresa_id: int, inicio: str, fim: str) -> list:
        data_inicio, data_fim = self._validar_periodo(inicio, fim)
        return self.repository.vendas_por_pico_hora(
            empresa_id=empresa_id,
            inicio=data_inicio,
            fim=data_fim,
        )

    def relatorio_diario(self, empresa_id: int, dia_str: str) -> dict:
        dia = self._validar_data(dia_str)
        return self.repository.obter_panoramico_diario(
            empresa_id=empresa_id,
            dia=dia,
        )

