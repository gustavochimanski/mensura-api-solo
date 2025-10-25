
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Dict, List, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.delivery.models.model_pedido_dv import PedidoDeliveryModel
from app.api.delivery.models.model_pedido_item_dv import PedidoItemModel
from app.api.delivery.models.model_pedido_status_historico_dv import (
    PedidoStatusHistoricoModel,
)
from app.api.delivery.models.model_entregador_dv import EntregadorDeliveryModel
from app.api.mensura.models.cadprod_model import ProdutoModel
from app.api.mesas.models.model_pedido_mesa import PedidoMesaModel


def _day_bounds(target_date: date) -> Tuple[datetime, datetime]:
    start = datetime.combine(target_date, time.min)
    end = start + timedelta(days=1)
    return start, end


def _previous_day(target_date: date) -> date:
    return target_date - timedelta(days=1)


def _previous_month_bounds(reference_date: date) -> Tuple[datetime, datetime]:
    first_day_current_month = reference_date.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)
    start = datetime.combine(first_day_previous_month, time.min)
    end = datetime.combine(first_day_current_month, time.min)
    return start, end


def _decimal_to_float(value: Decimal | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


@dataclass
class PeriodoResumo:
    quantidade: int
    faturamento: float


class RelatorioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _resumo_periodo(
        self, empresa_id: int, inicio: datetime, fim: datetime
    ) -> PeriodoResumo:
        # Considera todos os pedidos exceto cancelados (status != "C")
        # Isso inclui: P, I, R, S, E, D, X, A (Pendente, Impressão, Preparo, Saiu, Entregue, Editado, Em Edição, Aguardando)
        quantidade, faturamento = (
            self.db.query(
                func.count(PedidoDeliveryModel.id),
                func.coalesce(func.sum(PedidoDeliveryModel.valor_total), 0),
            )
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.data_criacao >= inicio,
                PedidoDeliveryModel.data_criacao < fim,
                PedidoDeliveryModel.status != "C",  # Exclui apenas cancelados
            )
            .one()
        )

        return PeriodoResumo(
            quantidade=int(quantidade or 0),
            faturamento=_decimal_to_float(faturamento),
        )

    def _media_tempo_entrega_minutos(
        self, empresa_id: int, inicio: datetime, fim: datetime
    ) -> float:
        # Calcular tempo médio para pedidos de delivery
        finalizacao_subquery = (
            self.db.query(
                PedidoStatusHistoricoModel.pedido_id.label("pedido_id"),
                func.max(PedidoStatusHistoricoModel.criado_em).label("finalizado_em"),
            )
            .filter(PedidoStatusHistoricoModel.status == "E")
            .group_by(PedidoStatusHistoricoModel.pedido_id)
            .subquery()
        )

        avg_seconds_delivery = (
            self.db.query(
                func.avg(
                    func.extract(
                        "epoch",
                        finalizacao_subquery.c.finalizado_em
                        - PedidoDeliveryModel.data_criacao,
                    )
                )
            )
            .select_from(PedidoDeliveryModel)
            .join(
                finalizacao_subquery,
                finalizacao_subquery.c.pedido_id == PedidoDeliveryModel.id,
            )
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.data_criacao >= inicio,
                PedidoDeliveryModel.data_criacao < fim,
                PedidoDeliveryModel.status != "C",  # Exclui apenas cancelados
            )
            .scalar()
        )

        # Calcular tempo médio para pedidos de mesa (entrega local)
        avg_seconds_mesa = (
            self.db.query(
                func.avg(
                    func.extract(
                        "epoch",
                        PedidoMesaModel.updated_at - PedidoMesaModel.created_at,
                    )
                )
            )
            .filter(
                PedidoMesaModel.status == "E",  # Status ENTREGUE
                PedidoMesaModel.created_at >= inicio,
                PedidoMesaModel.created_at < fim,
            )
            .scalar()
        )

        # Combinar os tempos médios (média ponderada)
        tempos = []
        if avg_seconds_delivery:
            tempos.append(float(avg_seconds_delivery))
        if avg_seconds_mesa:
            tempos.append(float(avg_seconds_mesa))

        if not tempos:
            return 0.0

        # Calcular média simples dos tempos
        tempo_medio_segundos = sum(tempos) / len(tempos)
        return round(tempo_medio_segundos / 60.0, 2)

    def _vendas_por_hora(
        self, empresa_id: int, inicio: datetime, fim: datetime
    ) -> List[Dict[str, float | int]]:
        rows = (
            self.db.query(
                func.date_part("hour", func.timezone('America/Sao_Paulo', PedidoDeliveryModel.data_criacao)).label("hora"),
                func.count(PedidoDeliveryModel.id).label("quantidade"),
                func.coalesce(func.sum(PedidoDeliveryModel.valor_total), 0).label(
                    "faturamento"
                ),
            )
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.data_criacao >= inicio,
                PedidoDeliveryModel.data_criacao < fim,
                PedidoDeliveryModel.status != "C",  # Exclui apenas cancelados
            )
            .group_by("hora")
            .order_by("hora")
            .all()
        )

        agrupado = {
            int(row.hora): {
                "hora": int(row.hora),
                "quantidade": int(row.quantidade or 0),
                "faturamento": _decimal_to_float(row.faturamento),
            }
            for row in rows
        }

        return [
            agrupado.get(
                hora,
                {"hora": hora, "quantidade": 0, "faturamento": 0.0},
            )
            for hora in range(24)
        ]

    def _top_produtos(
        self, empresa_id: int, inicio: datetime, fim: datetime, limite: int = 10
    ) -> List[Dict[str, float | int | str]]:
        descricao_expr = func.coalesce(
            PedidoItemModel.produto_descricao_snapshot,
            ProdutoModel.descricao,
            PedidoItemModel.produto_cod_barras,
        )

        rows = (
            self.db.query(
                descricao_expr.label("descricao"),
                func.sum(PedidoItemModel.quantidade).label("quantidade"),
                func.coalesce(
                    func.sum(
                        PedidoItemModel.quantidade * PedidoItemModel.preco_unitario
                    ),
                    0,
                ).label("faturamento"),
            )
            .join(
                PedidoDeliveryModel,
                PedidoDeliveryModel.id == PedidoItemModel.pedido_id,
            )
            .outerjoin(
                ProdutoModel,
                ProdutoModel.cod_barras == PedidoItemModel.produto_cod_barras,
            )
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.data_criacao >= inicio,
                PedidoDeliveryModel.data_criacao < fim,
                PedidoDeliveryModel.status != "C",  # Exclui apenas cancelados
            )
            .group_by(descricao_expr)
            .order_by(func.sum(PedidoItemModel.quantidade).desc())
            .limit(limite)
            .all()
        )

        return [
            {
                "descricao": row.descricao or "Não identificado",
                "quantidade": int(row.quantidade or 0),
                "faturamento": _decimal_to_float(row.faturamento),
            }
            for row in rows
        ]

    def _top_entregadores(
        self, empresa_id: int, inicio: datetime, fim: datetime, limite: int = 5
    ) -> List[Dict[str, float | int | str]]:
        rows = (
            self.db.query(
                EntregadorDeliveryModel.nome.label("nome"),
                EntregadorDeliveryModel.telefone.label("telefone"),
                func.count(PedidoDeliveryModel.id).label("quantidade_pedidos"),
                func.coalesce(
                    func.sum(PedidoDeliveryModel.valor_total),
                    0,
                ).label("faturamento_total"),
            )
            .join(
                PedidoDeliveryModel,
                PedidoDeliveryModel.entregador_id == EntregadorDeliveryModel.id,
            )
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.data_criacao >= inicio,
                PedidoDeliveryModel.data_criacao < fim,
                PedidoDeliveryModel.status != "C",  # Exclui apenas cancelados
                PedidoDeliveryModel.entregador_id.isnot(None),  # Apenas pedidos com entregador
            )
            .group_by(
                EntregadorDeliveryModel.id,
                EntregadorDeliveryModel.nome,
                EntregadorDeliveryModel.telefone,
            )
            .order_by(func.count(PedidoDeliveryModel.id).desc())
            .limit(limite)
            .all()
        )

        return [
            {
                "nome": row.nome or "Não identificado",
                "telefone": row.telefone or "Não informado",
                "quantidade_pedidos": int(row.quantidade_pedidos or 0),
                "faturamento_total": _decimal_to_float(row.faturamento_total),
            }
            for row in rows
        ]

    def obter_panoramico_diario(
        self, empresa_id: int, dia: date
    ) -> Dict[str, object]:
        inicio_dia, fim_dia = _day_bounds(dia)
        dia_anterior = _previous_day(dia)
        inicio_ontem, fim_ontem = _day_bounds(dia_anterior)
        inicio_mes_passado, fim_mes_passado = _previous_month_bounds(dia)

        resumo_dia = self._resumo_periodo(empresa_id, inicio_dia, fim_dia)
        resumo_ontem = self._resumo_periodo(empresa_id, inicio_ontem, fim_ontem)
        resumo_mes_passado = self._resumo_periodo(
            empresa_id, inicio_mes_passado, fim_mes_passado
        )

        ticket_medio_dia = (
            round(resumo_dia.faturamento / resumo_dia.quantidade, 2)
            if resumo_dia.quantidade
            else 0.0
        )
        ticket_medio_ontem = (
            round(resumo_ontem.faturamento / resumo_ontem.quantidade, 2)
            if resumo_ontem.quantidade
            else 0.0
        )
        ticket_medio_mes_passado = (
            round(resumo_mes_passado.faturamento / resumo_mes_passado.quantidade, 2)
            if resumo_mes_passado.quantidade
            else 0.0
        )

        tempo_medio = self._media_tempo_entrega_minutos(
            empresa_id, inicio_dia, fim_dia
        )

        return {
            "data": dia,
            "empresa": {
                "id": empresa_id,
            },
            "pedidos": {
                "dia": resumo_dia.quantidade,
                "ontem": resumo_ontem.quantidade,
                "mes_anterior": resumo_mes_passado.quantidade,
            },
            "faturamento": {
                "dia": resumo_dia.faturamento,
                "ontem": resumo_ontem.faturamento,
                "mes_anterior": resumo_mes_passado.faturamento,
            },
            "ticket_medio": {
                "dia": ticket_medio_dia,
                "ontem": ticket_medio_ontem,
                "mes_anterior": ticket_medio_mes_passado,
            },
            "tempo_entrega": {
                "medio_minutos": tempo_medio,
            },
            "vendas_por_hora": self._vendas_por_hora(empresa_id, inicio_dia, fim_dia),
            "top_produtos": self._top_produtos(empresa_id, inicio_dia, fim_dia),
            "top_entregadores": self._top_entregadores(empresa_id, inicio_dia, fim_dia),
        }

