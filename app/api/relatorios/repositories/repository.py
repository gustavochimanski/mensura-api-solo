
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple
import calendar

from sqlalchemy import func, cast, String, literal
from sqlalchemy.orm import Session
from sqlalchemy.exc import ProgrammingError, InternalError

from app.api.pedidos.models.model_pedido_unificado import (
    PedidoUnificadoModel,
    TipoPedido,
)
from app.api.pedidos.models.model_pedido_item_unificado import PedidoItemUnificadoModel
from app.api.pedidos.models.model_pedido_historico_unificado import (
    PedidoHistoricoUnificadoModel,
)
from app.api.cadastros.models.model_entregador_dv import EntregadorDeliveryModel
from app.api.cadastros.models.model_endereco_dv import EnderecoModel
from app.api.catalogo.models.model_produto import ProdutoModel
from app.api.pedidos.models.model_pedido_unificado import StatusPedido


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
    """Converte Decimal/float para float com 2 casas decimais (meia para cima)."""
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        try:
            return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        except Exception:
            try:
                return float(value)
            except Exception:
                return 0.0
    try:
        return round(float(value), 2)
    except Exception:
        return 0.0

def _shift_month_safe(d: date, months: int) -> date:
    """Desloca a data para outro mês mantendo o dia quando possível, usando último dia do mês destino quando necessário."""
    year = d.year + ((d.month - 1 + months) // 12)
    month = ((d.month - 1 + months) % 12) + 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(d.day, last_day)
    return date(year, month, day)


@dataclass
class PeriodoResumo:
    quantidade: int
    faturamento: float


class RelatorioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _handle_db_error(self, fn, default_return=None):
        """
        Executa uma função de query com tratamento de erros de transação.
        Se a transação estiver abortada, faz rollback e tenta novamente.
        """
        try:
            return fn()
        except InternalError as e:
            # Se a transação foi abortada, faz rollback e tenta novamente
            if "transaction is aborted" in str(e):
                self.db.rollback()
                try:
                    return fn()
                except (ProgrammingError, InternalError) as retry_e:
                    if "does not exist" in str(retry_e):
                        return default_return if default_return is not None else []
                    raise
            raise
        except ProgrammingError as e:
            if "does not exist" in str(e):
                return default_return if default_return is not None else []
            raise

    def _resumo_periodo(
        self, empresa_id: int, inicio: datetime, fim: datetime
    ) -> PeriodoResumo:
        quantidade_total = 0
        faturamento_total = Decimal("0")

        def _query_delivery():
            return (
                self.db.query(
                    func.count(PedidoUnificadoModel.id),
                    func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0),
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != "C",
                )
                .first()
                or (0, 0)
            )

        def _query_mesa():
            return (
                self.db.query(
                    func.count(PedidoUnificadoModel.id),
                    func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0),
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.MESA.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != StatusPedido.CANCELADO.value,
                )
                .first()
                or (0, 0)
            )

        def _query_balcao():
            return (
                self.db.query(
                    func.count(PedidoUnificadoModel.id),
                    func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0),
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.BALCAO.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != StatusPedido.CANCELADO.value,
                )
                .first()
                or (0, 0)
            )

        # Delivery (usando modelo unificado)
        qtd_delivery, fatur_delivery = self._handle_db_error(_query_delivery, default_return=(0, 0))
        quantidade_total += int(qtd_delivery or 0)
        faturamento_total += Decimal(str(fatur_delivery or 0))

        # Mesa - usando modelo unificado
        qtd_mesa, fatur_mesa = self._handle_db_error(_query_mesa, default_return=(0, 0))
        quantidade_total += int(qtd_mesa or 0)
        faturamento_total += Decimal(str(fatur_mesa or 0))

        # Balcão - usando modelo unificado
        qtd_balcao, fatur_balcao = self._handle_db_error(_query_balcao, default_return=(0, 0))
        quantidade_total += int(qtd_balcao or 0)
        faturamento_total += Decimal(str(fatur_balcao or 0))

        return PeriodoResumo(
            quantidade=quantidade_total,
            faturamento=_decimal_to_float(faturamento_total),
        )

    def _cancelados_periodo(
        self, empresa_id: int, inicio: datetime, fim: datetime
    ) -> int:
        """Conta pedidos cancelados (status = 'C') no período."""
        total_cancelados = 0

        def _query_delivery():
            return (
                self.db.query(func.count(PedidoUnificadoModel.id))
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status == "C",
                )
                .scalar()
            )

        def _query_mesa():
            return (
                self.db.query(func.count(PedidoUnificadoModel.id))
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.MESA.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status == StatusPedido.CANCELADO.value,
                )
                .scalar()
            )

        def _query_balcao():
            return (
                self.db.query(func.count(PedidoUnificadoModel.id))
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.BALCAO.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status == StatusPedido.CANCELADO.value,
                )
                .scalar()
            )

        cancelados_delivery = self._handle_db_error(_query_delivery, default_return=0)
        total_cancelados += int(cancelados_delivery or 0)

        cancelados_mesa = self._handle_db_error(_query_mesa, default_return=0)
        total_cancelados += int(cancelados_mesa or 0)

        cancelados_balcao = self._handle_db_error(_query_balcao, default_return=0)
        total_cancelados += int(cancelados_balcao or 0)

        return total_cancelados

    def _media_tempo_entrega_minutos(
        self, empresa_id: int, inicio: datetime, fim: datetime
    ) -> tuple[float, float]:
        def _query_delivery():
            return (
                self.db.query(PedidoUnificadoModel)
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status == "E",  # Apenas entregues
                )
                .all()
            )

        def _query_mesa():
            return (
                self.db.query(PedidoUnificadoModel)
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.MESA.value,
                    PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value,
                    PedidoUnificadoModel.mesa_id.isnot(None),
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                )
                .all()
            )

        def _query_balcao():
            return (
                self.db.query(PedidoUnificadoModel)
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.BALCAO.value,
                    PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                )
                .all()
            )

        # Calcular tempo médio para pedidos de delivery
        # Buscar pedidos entregues (status E) no período
        pedidos_delivery_entregues = self._handle_db_error(_query_delivery, default_return=[])
        if pedidos_delivery_entregues is None:
            return 0.0, 0.0
        
        # Calcular tempo médio para pedidos de mesa (entrega local)
        # Buscar pedidos de mesa que foram entregues no período
        pedidos_mesa_entregues = self._handle_db_error(_query_mesa, default_return=[])
        pedidos_balcao_entregues = self._handle_db_error(_query_balcao, default_return=[])

        # Calcular tempo médio para delivery
        tempo_delivery_minutos = 0.0
        if pedidos_delivery_entregues:
            tempos_delivery = []
            for pedido in pedidos_delivery_entregues:
                # Buscar quando foi finalizado (status E no histórico)
                # Tenta primeiro com modelo unificado, depois com modelo antigo
                finalizacao = (
                    self.db.query(PedidoHistoricoUnificadoModel.created_at)
                    .filter(
                        PedidoHistoricoUnificadoModel.pedido_id == pedido.id,
                        PedidoHistoricoUnificadoModel.status_novo == "E"
                    )
                    .order_by(PedidoHistoricoUnificadoModel.created_at.desc())
                    .first()
                )
                
                if finalizacao:
                    tempo_segundos = (finalizacao[0] - pedido.created_at).total_seconds()
                    if tempo_segundos > 0:
                        tempos_delivery.append(tempo_segundos)
                else:
                    # Fallback: usar updated_at se não encontrar no histórico
                    tempo_segundos = (pedido.updated_at - pedido.created_at).total_seconds()
                    if tempo_segundos > 0:
                        tempos_delivery.append(tempo_segundos)
            
            if tempos_delivery:
                tempo_medio_segundos = sum(tempos_delivery) / len(tempos_delivery)
                tempo_delivery_minutos = round(tempo_medio_segundos / 60.0, 2)

        # Calcular tempo médio para pedidos presenciais (mesa + balcão)
        tempos_locais: list[float] = []

        for pedido in pedidos_mesa_entregues:
            if pedido.updated_at and pedido.created_at:
                tempo_segundos = (pedido.updated_at - pedido.created_at).total_seconds()
                if tempo_segundos > 0:
                    tempos_locais.append(tempo_segundos)
        
        for pedido in pedidos_balcao_entregues:
            if pedido.updated_at and pedido.created_at:
                tempo_segundos = (pedido.updated_at - pedido.created_at).total_seconds()
                if tempo_segundos > 0:
                    tempos_locais.append(tempo_segundos)

        tempo_local_minutos = (
            round(sum(tempos_locais) / len(tempos_locais) / 60.0, 2)
            if tempos_locais
            else 0.0
        )
        
        return tempo_delivery_minutos, tempo_local_minutos

    def _vendas_por_hora(
        self, empresa_id: int, inicio: datetime, fim: datetime
    ) -> List[Dict[str, float | int]]:
        def _rows_delivery():
            return (
                self.db.query(
                    func.date_part("hour", func.timezone('America/Sao_Paulo', PedidoUnificadoModel.created_at)).label("hora"),
                    func.count(PedidoUnificadoModel.id).label("quantidade"),
                    func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0).label("faturamento"),
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != "C",
                )
                .group_by("hora")
                .all()
            )

        def _rows_mesa():
            return (
                self.db.query(
                    func.date_part("hour", func.timezone('America/Sao_Paulo', PedidoUnificadoModel.created_at)).label("hora"),
                    func.count(PedidoUnificadoModel.id).label("quantidade"),
                    func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0).label("faturamento"),
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.MESA.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != StatusPedido.CANCELADO.value,
                )
                .group_by("hora")
                .all()
            )

        def _rows_balcao():
            return (
                self.db.query(
                    func.date_part("hour", func.timezone('America/Sao_Paulo', PedidoUnificadoModel.created_at)).label("hora"),
                    func.count(PedidoUnificadoModel.id).label("quantidade"),
                    func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0).label("faturamento"),
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.BALCAO.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != StatusPedido.CANCELADO.value,
                )
                .group_by("hora")
                .all()
            )

        rows_delivery = self._handle_db_error(_rows_delivery, default_return=[])
        rows_mesa = self._handle_db_error(_rows_mesa, default_return=[])
        rows_balcao = self._handle_db_error(_rows_balcao, default_return=[])

        agregados: dict[int, dict[str, float | int]] = {}

        def _acumular(rows):
            for row in rows:
                hora = int(row.hora)
                bucket = agregados.setdefault(hora, {"hora": hora, "quantidade": 0, "faturamento": 0.0})
                bucket["quantidade"] = int(bucket["quantidade"]) + int(row.quantidade or 0)
                bucket["faturamento"] = float(bucket["faturamento"]) + _decimal_to_float(row.faturamento)

        _acumular(rows_delivery)
        _acumular(rows_mesa)
        _acumular(rows_balcao)

        return [
            agregados.get(
                hora,
                {"hora": hora, "quantidade": 0, "faturamento": 0.0},
            )
            for hora in range(24)
        ]

    def _vendas_por_dia(
        self, empresa_id: int, inicio: datetime, fim: datetime
    ) -> List[Dict[str, float | int | str]]:
        """Agrega por dia (timezone America/Sao_Paulo) retornando lista ordenada por dia."""
        def _query():
            return (
                self.db.query(
                    func.date_trunc(
                        "day",
                        func.timezone('America/Sao_Paulo', PedidoUnificadoModel.created_at),
                    ).label("dia"),
                    func.count(PedidoUnificadoModel.id).label("quantidade"),
                    func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0).label(
                        "faturamento"
                    ),
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != "C",
                )
                .group_by("dia")
                .order_by("dia")
                .all()
            )
        
        rows = self._handle_db_error(_query, default_return=[])

        resultados: List[Dict[str, float | int | str]] = []
        for row in rows:
            quantidade = int(row.quantidade or 0)
            faturamento = _decimal_to_float(row.faturamento)
            ticket_medio = round(faturamento / quantidade, 2) if quantidade else 0.0
            resultados.append({
                "data": row.dia.date().isoformat(),
                "quantidade": quantidade,
                "faturamento": faturamento,
                "ticket_medio": ticket_medio,
            })
        return resultados

    def _top_produtos(
        self, empresa_id: int, inicio: datetime, fim: datetime, limite: int = 10
    ) -> List[Dict[str, float | int | str]]:
        def _query_itens(
            itens_model,
            pedido_model,
            pedido_criacao_attr,
            status_cancelado_value,
        ):
            descricao_expr_local = func.coalesce(
                itens_model.produto_descricao_snapshot,
                ProdutoModel.descricao,
                itens_model.produto_cod_barras,
            )

            return (
                self.db.query(
                    descricao_expr_local.label("descricao"),
                    func.sum(itens_model.quantidade).label("quantidade"),
                    func.coalesce(
                        func.sum(itens_model.quantidade * itens_model.preco_unitario), 0
                    ).label("faturamento"),
                )
                .join(pedido_model, pedido_model.id == itens_model.pedido_id)
                .outerjoin(ProdutoModel, ProdutoModel.cod_barras == itens_model.produto_cod_barras)
                .filter(
                    pedido_model.empresa_id == empresa_id,
                    pedido_criacao_attr >= inicio,
                    pedido_criacao_attr < fim,
                    pedido_model.status != status_cancelado_value,
                )
                .group_by(descricao_expr_local)
                .all()
            )

        def _query_delivery():
            descricao_expr_delivery = func.coalesce(
                PedidoItemUnificadoModel.produto_descricao_snapshot,
                ProdutoModel.descricao,
                PedidoItemUnificadoModel.produto_cod_barras,
            )
            return (
                self.db.query(
                    descricao_expr_delivery.label("descricao"),
                    func.sum(PedidoItemUnificadoModel.quantidade).label("quantidade"),
                    func.coalesce(
                        func.sum(PedidoItemUnificadoModel.quantidade * PedidoItemUnificadoModel.preco_unitario), 0
                    ).label("faturamento"),
                )
                .join(PedidoUnificadoModel, PedidoUnificadoModel.id == PedidoItemUnificadoModel.pedido_id)
                .outerjoin(ProdutoModel, ProdutoModel.cod_barras == PedidoItemUnificadoModel.produto_cod_barras)
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != "C",
                )
                .group_by(descricao_expr_delivery)
                .all()
            )

        def _query_mesa():
            descricao_expr_mesa = func.coalesce(
                PedidoItemUnificadoModel.produto_descricao_snapshot,
                ProdutoModel.descricao,
                PedidoItemUnificadoModel.produto_cod_barras,
            )
            return (
                self.db.query(
                    descricao_expr_mesa.label("descricao"),
                    func.sum(PedidoItemUnificadoModel.quantidade).label("quantidade"),
                    func.coalesce(
                        func.sum(PedidoItemUnificadoModel.quantidade * PedidoItemUnificadoModel.preco_unitario), 0
                    ).label("faturamento"),
                )
                .join(PedidoUnificadoModel, PedidoUnificadoModel.id == PedidoItemUnificadoModel.pedido_id)
                .outerjoin(ProdutoModel, ProdutoModel.cod_barras == PedidoItemUnificadoModel.produto_cod_barras)
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.MESA.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != StatusPedido.CANCELADO.value,
                )
                .group_by(descricao_expr_mesa)
                .all()
            )

        def _query_balcao():
            descricao_expr_balcao = func.coalesce(
                PedidoItemUnificadoModel.produto_descricao_snapshot,
                ProdutoModel.descricao,
                PedidoItemUnificadoModel.produto_cod_barras,
            )
            return (
                self.db.query(
                    descricao_expr_balcao.label("descricao"),
                    func.sum(PedidoItemUnificadoModel.quantidade).label("quantidade"),
                    func.coalesce(
                        func.sum(PedidoItemUnificadoModel.quantidade * PedidoItemUnificadoModel.preco_unitario), 0
                    ).label("faturamento"),
                )
                .join(PedidoUnificadoModel, PedidoUnificadoModel.id == PedidoItemUnificadoModel.pedido_id)
                .outerjoin(ProdutoModel, ProdutoModel.cod_barras == PedidoItemUnificadoModel.produto_cod_barras)
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.BALCAO.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != StatusPedido.CANCELADO.value,
                )
                .group_by(descricao_expr_balcao)
                .all()
            )

        rows_delivery = self._handle_db_error(_query_delivery, default_return=[])
        rows_mesa = self._handle_db_error(_query_mesa, default_return=[])
        rows_balcao = self._handle_db_error(_query_balcao, default_return=[])

        acumulado: dict[str, dict[str, float | int | str]] = {}

        def _somar(rows):
            for row in rows:
                key = row.descricao or "Não identificado"
                entry = acumulado.setdefault(
                    key,
                    {"descricao": key, "quantidade": 0, "faturamento": 0.0},
                )
                entry["quantidade"] = int(entry["quantidade"]) + int(row.quantidade or 0)
                entry["faturamento"] = float(entry["faturamento"]) + _decimal_to_float(row.faturamento)

        _somar(rows_delivery)
        _somar(rows_mesa)
        _somar(rows_balcao)

        return sorted(
            acumulado.values(),
            key=lambda item: item["quantidade"],
            reverse=True,
        )[:limite]

    def _top_entregadores(
        self, empresa_id: int, inicio: datetime, fim: datetime, limite: int = 5
    ) -> List[Dict[str, float | int | str]]:
        def _query():
            return (
                self.db.query(
                    EntregadorDeliveryModel.nome.label("nome"),
                    EntregadorDeliveryModel.telefone.label("telefone"),
                    func.count(PedidoUnificadoModel.id).label("quantidade_pedidos"),
                    func.coalesce(
                        func.sum(PedidoUnificadoModel.valor_total),
                        0,
                    ).label("faturamento_total"),
                )
                .join(
                    PedidoUnificadoModel,
                    PedidoUnificadoModel.entregador_id == EntregadorDeliveryModel.id,
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                    PedidoUnificadoModel.created_at >= inicio,
                    PedidoUnificadoModel.created_at < fim,
                    PedidoUnificadoModel.status != "C",  # Exclui apenas cancelados
                    PedidoUnificadoModel.entregador_id.isnot(None),  # Apenas pedidos com entregador
                )
                .group_by(
                    EntregadorDeliveryModel.id,
                    EntregadorDeliveryModel.nome,
                    EntregadorDeliveryModel.telefone,
                )
                .order_by(func.count(PedidoUnificadoModel.id).desc())
                .limit(limite)
                .all()
            )
        
        rows = self._handle_db_error(_query, default_return=[])

        return [
            {
                "nome": row.nome or "Não identificado",
                "telefone": row.telefone or "Não informado",
                "quantidade_pedidos": int(row.quantidade_pedidos or 0),
                "faturamento_total": _decimal_to_float(row.faturamento_total),
            }
            for row in rows
        ]

    def obter_panoramico_periodo(
        self,
        empresa_id: int,
        inicio: date,
        fim: date,
    ) -> Dict[str, object]:
        inicio_periodo = datetime.combine(inicio, time.min)
        fim_periodo = datetime.combine(fim + timedelta(days=1), time.min)

        resumo_periodo = self._resumo_periodo(empresa_id, inicio_periodo, fim_periodo)
        cancelados_periodo = self._cancelados_periodo(empresa_id, inicio_periodo, fim_periodo)

        # Período anterior: MESMO INTERVALO no mês anterior (ex.: 10-20 vs 10-20 do mês passado)
        inicio_prev = _shift_month_safe(inicio, -1)
        fim_prev = _shift_month_safe(fim, -1)
        inicio_periodo_anterior = datetime.combine(inicio_prev, time.min)
        fim_periodo_anterior = datetime.combine(fim_prev + timedelta(days=1), time.min)
        resumo_periodo_anterior = self._resumo_periodo(
            empresa_id,
            inicio_periodo_anterior,
            fim_periodo_anterior,
        )
        cancelados_periodo_anterior = self._cancelados_periodo(
            empresa_id, inicio_periodo_anterior, fim_periodo_anterior
        )

        ticket_medio_periodo = (
            round(resumo_periodo.faturamento / resumo_periodo.quantidade, 2)
            if resumo_periodo.quantidade
            else 0.0
        )
        ticket_medio_periodo_anterior = (
            round(
                resumo_periodo_anterior.faturamento
                / resumo_periodo_anterior.quantidade,
                2,
            )
            if resumo_periodo_anterior.quantidade
            else 0.0
        )

        tempo_medio_delivery, tempo_medio_local = self._media_tempo_entrega_minutos(
            empresa_id,
            inicio_periodo,
            fim_periodo,
        )

        return {
            "periodo": {
                "inicio": inicio,
                "fim": fim,
            },
            "empresa": {
                "id": empresa_id,
            },
            "pedidos": {
                "periodo": resumo_periodo.quantidade,
                "periodo_anterior": resumo_periodo_anterior.quantidade,
            },
            "cancelados": {
                "periodo": cancelados_periodo,
                "periodo_anterior": cancelados_periodo_anterior,
            },
            "faturamento": {
                "periodo": resumo_periodo.faturamento,
                "periodo_anterior": resumo_periodo_anterior.faturamento,
            },
            "ticket_medio": {
                "periodo": ticket_medio_periodo,
                "periodo_anterior": ticket_medio_periodo_anterior,
            },
            "tempo_entrega": {
                "delivery_minutos": tempo_medio_delivery,
                "local_minutos": tempo_medio_local,
            },
            "vendas_por_hora": self._vendas_por_hora(
                empresa_id,
                inicio_periodo,
                fim_periodo,
            ),
            "top_produtos": self._top_produtos(
                empresa_id,
                inicio_periodo,
                fim_periodo,
            ),
            "top_entregadores": self._top_entregadores(
                empresa_id,
                inicio_periodo,
                fim_periodo,
            ),
        }

    def obter_panoramico_mes_anterior(
        self,
        empresa_id: int,
        referencia: date,
    ) -> Dict[str, object]:
        """[DEPRECATED] Mantido por compatibilidade, mas o panorâmico principal não usa mais 'mês anterior'."""
        inicio_mes_passado, fim_mes_passado = _previous_month_bounds(referencia)

        resumo_mes_passado = self._resumo_periodo(
            empresa_id,
            inicio_mes_passado,
            fim_mes_passado,
        )

        ticket_medio_mes_passado = (
            round(
                resumo_mes_passado.faturamento / resumo_mes_passado.quantidade,
                2,
            )
            if resumo_mes_passado.quantidade
            else 0.0
        )

        tempo_medio_delivery, tempo_medio_local = self._media_tempo_entrega_minutos(
            empresa_id,
            inicio_mes_passado,
            fim_mes_passado,
        )

        return {
            "periodo": {
                "inicio": inicio_mes_passado.date(),
                "fim": (fim_mes_passado - timedelta(days=1)).date(),
            },
            "empresa": {"id": empresa_id},
            "pedidos": {"mes_anterior": resumo_mes_passado.quantidade},
            "faturamento": {"mes_anterior": resumo_mes_passado.faturamento},
            "ticket_medio": {"mes_anterior": ticket_medio_mes_passado},
            "tempo_entrega": {
                "delivery_minutos": tempo_medio_delivery,
                "local_minutos": tempo_medio_local,
            },
            "vendas_por_hora": self._vendas_por_hora(
                empresa_id,
                inicio_mes_passado,
                fim_mes_passado,
            ),
            "top_produtos": self._top_produtos(
                empresa_id,
                inicio_mes_passado,
                fim_mes_passado,
            ),
            "top_entregadores": self._top_entregadores(
                empresa_id,
                inicio_mes_passado,
                fim_mes_passado,
            ),
        }

    def ranking_por_bairro(
        self,
        empresa_id: int,
        inicio: date,
        fim: date,
        limite: int = 10,
    ) -> List[Dict[str, object]]:
        inicio_dt = datetime.combine(inicio, time.min)
        fim_dt = datetime.combine(fim + timedelta(days=1), time.min)

        bairro_expr = func.coalesce(
            cast(PedidoUnificadoModel.endereco_snapshot['bairro'].astext, String),
            EnderecoModel.bairro,
            literal("Não informado"),
        )

        def _query():
            return (
                self.db.query(
                    bairro_expr.label("bairro"),
                    func.count(PedidoUnificadoModel.id).label("quantidade"),
                    func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0).label("faturamento"),
                )
                .outerjoin(
                    EnderecoModel,
                    EnderecoModel.id == PedidoUnificadoModel.endereco_id,
                )
                .filter(
                    PedidoUnificadoModel.empresa_id == empresa_id,
                    PedidoUnificadoModel.tipo_pedido == TipoPedido.DELIVERY.value,
                    PedidoUnificadoModel.created_at >= inicio_dt,
                    PedidoUnificadoModel.created_at < fim_dt,
                    PedidoUnificadoModel.status != "C",
                )
                .group_by(bairro_expr)
                .order_by(func.coalesce(func.sum(PedidoUnificadoModel.valor_total), 0).desc())
                .limit(limite)
                .all()
            )
        
        rows = self._handle_db_error(_query, default_return=[])

        return [
            {
                "bairro": (row.bairro or "Não informado"),
                "quantidade": int(row.quantidade or 0),
                "faturamento": _decimal_to_float(row.faturamento),
            }
            for row in rows
        ]

    def vendas_ultimos_7_dias_comparativo(
        self,
        empresa_id: int,
        referencia: date,
    ) -> Dict[str, object]:
        atual_inicio = referencia - timedelta(days=6)
        atual_fim = referencia + timedelta(days=1)
        anterior_inicio = atual_inicio - timedelta(days=7)
        anterior_fim = atual_inicio

        atual = self._vendas_por_dia(
            empresa_id,
            datetime.combine(atual_inicio, time.min),
            datetime.combine(atual_fim, time.min),
        )
        anterior = self._vendas_por_dia(
            empresa_id,
            datetime.combine(anterior_inicio, time.min),
            datetime.combine(anterior_fim, time.min),
        )

        # Normalize as datas em listas indexadas por string ISO (para alinhar)
        def to_map(rows: List[Dict[str, object]]) -> Dict[str, Dict[str, object]]:
            return {r["data"]: r for r in rows}

        atual_map = to_map(atual)
        anterior_map = to_map(anterior)

        dias_atual = [
            (atual_inicio + timedelta(days=i)).isoformat() for i in range(7)
        ]
        dias_anterior = [
            (anterior_inicio + timedelta(days=i)).isoformat() for i in range(7)
        ]

        serie_atual = [
            atual_map.get(
                d,
                {"data": d, "quantidade": 0, "faturamento": 0.0},
            )
            for d in dias_atual
        ]
        serie_anterior = [
            anterior_map.get(
                d,
                {"data": d, "quantidade": 0, "faturamento": 0.0},
            )
            for d in dias_anterior
        ]

        # Cálculo das variações percentuais vs. ontem (apenas do período atual)
        variacao_percentual_vs_ontem = {
            "quantidade": 0.0,
            "faturamento": 0.0,
            "ticket_medio": 0.0,
        }

        if len(serie_atual) >= 2:
            hoje = serie_atual[-1]
            ontem = serie_atual[-2]

            q_ant = float(ontem.get("quantidade", 0) or 0)
            q_atu = float(hoje.get("quantidade", 0) or 0)
            f_ant = float(ontem.get("faturamento", 0.0) or 0.0)
            f_atu = float(hoje.get("faturamento", 0.0) or 0.0)
            t_ant = float(ontem.get("ticket_medio", 0.0) or 0.0)
            t_atu = float(hoje.get("ticket_medio", 0.0) or 0.0)

            def pct(atual: float, anterior: float) -> float:
                if anterior == 0:
                    return 100.0 if atual > 0 else 0.0
                return round(((atual - anterior) / anterior) * 100.0, 2)

            variacao_percentual_vs_ontem = {
                "quantidade": pct(q_atu, q_ant),
                "faturamento": pct(f_atu, f_ant),
                "ticket_medio": pct(t_atu, t_ant),
            }

        return {
            "dias_atual": dias_atual,
            "dias_anterior": dias_anterior,
            "atual": serie_atual,
            "anterior": serie_anterior,
            "variacao_percentual_vs_ontem": variacao_percentual_vs_ontem,
        }

    def vendas_por_pico_hora(
        self,
        empresa_id: int,
        inicio: date,
        fim: date,
    ) -> List[Dict[str, object]]:
        inicio_dt = datetime.combine(inicio, time.min)
        fim_dt = datetime.combine(fim + timedelta(days=1), time.min)
        return self._vendas_por_hora(empresa_id, inicio_dt, fim_dt)

    def obter_panoramico_diario(
        self,
        empresa_id: int,
        dia: date,
    ) -> Dict[str, object]:
        """Panorâmico de um único dia, comparando sempre com ontem."""
        inicio_periodo = datetime.combine(dia, time.min)
        fim_periodo = datetime.combine(dia + timedelta(days=1), time.min)

        ontem = dia - timedelta(days=1)
        inicio_ontem = datetime.combine(ontem, time.min)
        fim_ontem = datetime.combine(dia, time.min)

        resumo_hoje = self._resumo_periodo(empresa_id, inicio_periodo, fim_periodo)
        resumo_ontem = self._resumo_periodo(empresa_id, inicio_ontem, fim_ontem)
        cancelados_hoje = self._cancelados_periodo(empresa_id, inicio_periodo, fim_periodo)
        cancelados_ontem = self._cancelados_periodo(empresa_id, inicio_ontem, fim_ontem)

        fatur_hoje = float(resumo_hoje.faturamento or 0.0)
        qtd_hoje = int(resumo_hoje.quantidade or 0)
        ticket_hoje = round(fatur_hoje / qtd_hoje, 2) if qtd_hoje else 0.0

        fatur_ontem = float(resumo_ontem.faturamento or 0.0)
        qtd_ontem = int(resumo_ontem.quantidade or 0)
        ticket_ontem = round(fatur_ontem / qtd_ontem, 2) if qtd_ontem else 0.0

        tempo_medio_delivery, tempo_medio_local = self._media_tempo_entrega_minutos(
            empresa_id, inicio_periodo, fim_periodo
        )

        return {
            "periodo": {"inicio": dia, "fim": dia},
            "empresa": {"id": empresa_id},
            "pedidos": {
                "periodo": resumo_hoje.quantidade,
                "periodo_anterior": resumo_ontem.quantidade,
            },
            "cancelados": {
                "periodo": cancelados_hoje,
                "periodo_anterior": cancelados_ontem,
            },
            "faturamento": {
                "periodo": resumo_hoje.faturamento,
                "periodo_anterior": resumo_ontem.faturamento,
            },
            "ticket_medio": {
                "periodo": ticket_hoje,
                "periodo_anterior": ticket_ontem,
            },
            "tempo_entrega": {
                "delivery_minutos": tempo_medio_delivery,
                "local_minutos": tempo_medio_local,
            },
            "vendas_por_hora": self._vendas_por_hora(empresa_id, inicio_periodo, fim_periodo),
            "top_produtos": self._top_produtos(empresa_id, inicio_periodo, fim_periodo),
            "top_entregadores": self._top_entregadores(empresa_id, inicio_periodo, fim_periodo),
        }

