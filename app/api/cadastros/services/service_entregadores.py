from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, case, cast, Date, exists, and_

from app.api.empresas.repositories.empresa_repo import EmpresaRepository
from app.api.cadastros.repositories.repo_entregadores import EntregadorRepository
from app.api.cadastros.schemas.schema_entregador import (
    EntregadorCreate,
    EntregadorUpdate,
    EntregadorRelatorioDetalhadoOut,
    EntregadorRelatorioDiaOut,
    EntregadorRelatorioDiaAcertoOut,
    EntregadorRelatorioEmpresaOut,
)
from app.api.pedidos.models.model_pedido_unificado import (
    PedidoUnificadoModel,
    TipoEntrega,
    StatusPedido,
)
from app.api.cardapio.models.model_transacao_pagamento_dv import TransacaoPagamentoModel
from app.utils.logger import logger

class EntregadoresService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = EntregadorRepository(db)
        self.empresa_repo = EmpresaRepository(db)

    @staticmethod
    def _to_money(value) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except Exception:
            try:
                from decimal import Decimal
                return float(Decimal(str(value)))
            except Exception:
                return 0.0

    @staticmethod
    def _normalize_period(inicio: datetime, fim: datetime) -> tuple[datetime, datetime]:
        # mesmo comportamento usado em AcertoEntregadoresService
        from datetime import timedelta as _td

        if (
            getattr(fim, "hour", 0) == 0
            and getattr(fim, "minute", 0) == 0
            and getattr(fim, "second", 0) == 0
            and getattr(fim, "microsecond", 0) == 0
        ):
            fim_exclusive = fim + _td(days=1)
        else:
            fim_exclusive = fim + _td(microseconds=1)
        return inicio, fim_exclusive

    def list(self):
        return self.repo.list()

    def get(self, id_: int):
        obj = self.repo.get(id_)
        if not obj:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Entregador não encontrado")
        return obj

    def create(self, data: EntregadorCreate):
        try:
            logger.info(f"[EntregadoresService] Tentando criar entregador: nome={getattr(data, 'nome', 'N/A')}, empresa_id={getattr(data, 'empresa_id', 'N/A')}")
            
            # Verifica se a empresa existe antes de criar o entregador
            if hasattr(data, 'empresa_id') and data.empresa_id:
                empresa = self.empresa_repo.get_empresa_by_id(data.empresa_id)
                if not empresa:
                    error_msg = f"Empresa com ID {data.empresa_id} não encontrada"
                    logger.error(f"[EntregadoresService] {error_msg}")
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        error_msg
                    )
            
            result = self.repo.create_with_empresa(**data.model_dump(exclude_unset=True))
            logger.info(f"[EntregadoresService] Entregador criado com sucesso: ID={result.id}")
            return result
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            # Trata erros de chave estrangeira
            if "foreign key" in error_msg.lower() or "violates foreign key constraint" in error_msg.lower():
                if "empresa" in error_msg.lower():
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Empresa com ID {data.empresa_id} não encontrada"
                    )
                else:
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        "Erro ao criar entregador: referência inválida"
                    )
            

            # Trata outros erros de integridade
            logger.error(f"[EntregadoresService] Erro de integridade ao criar entregador: {error_msg}")
            logger.error(f"[EntregadoresService] Dados recebidos: {data.model_dump()}")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Erro ao criar entregador: {error_msg}"
            )
        except HTTPException as http_exc:
            # Re-loga HTTPExceptions com mais detalhes
            logger.error(f"[EntregadoresService] HTTPException: {http_exc.status_code} - {http_exc.detail}")
            raise
        except Exception as e:
            self.db.rollback()
            import traceback
            logger.error(f"[EntregadoresService] Erro inesperado ao criar entregador: {str(e)}")
            logger.error(f"[EntregadoresService] Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Erro ao criar entregador: {str(e)}"
            )

    def update(self, id_: int, data: EntregadorUpdate):
        obj = self.get(id_)
        return self.repo.update(obj, **data.model_dump(exclude_none=True))

    def vincular_empresa(self, entregador_id: int, empresa_id: int):
        try:
            # primeiro garante que o entregador existe
            self.get(entregador_id)
            
            # Verifica se a empresa existe
            empresa = self.empresa_repo.get_empresa_by_id(empresa_id)
            if not empresa:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    f"Empresa com ID {empresa_id} não encontrada"
                )
            
            self.repo.vincular_empresa(entregador_id, empresa_id)
            return self.get(entregador_id)  # retorna o entregador atualizado
        except IntegrityError as e:
            self.db.rollback()
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            
            if "foreign key" in error_msg.lower() or "violates foreign key constraint" in error_msg.lower():
                if "empresa" in error_msg.lower():
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        f"Empresa com ID {empresa_id} não encontrada"
                    )
            
            logger.error(f"Erro ao vincular empresa: {error_msg}")
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Erro ao vincular empresa ao entregador"
            )
        except HTTPException:
            raise
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro inesperado ao vincular empresa: {str(e)}")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Erro ao vincular empresa: {str(e)}"
            )

    def desvincular_empresa(self, entregador_id: int, empresa_id: int):
        try:
            # garante que o entregador existe
            self.get(entregador_id)
            self.repo.desvincular_empresa(entregador_id, empresa_id)
            return self.get(entregador_id)  # retorna o entregador atualizado
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao desvincular empresa: {str(e)}")
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                f"Erro ao desvincular empresa: {str(e)}"
            )

    def delete(self, id_: int):
        obj = self.get(id_)
        self.repo.delete(obj)
        return {"ok": True}

    # ------------------- Relatório detalhado -------------------
    def relatorio_detalhado(
        self,
        *,
        entregador_id: int,
        inicio: datetime,
        fim: datetime,
    ) -> EntregadorRelatorioDetalhadoOut:
        inicio, fim_exclusive = self._normalize_period(inicio, fim)

        entregador = self.repo.get(entregador_id)
        if not entregador:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Entregador não encontrado")

        empresa_ids = [e.id for e in getattr(entregador, "empresas", [])]
        empresa_nome_map = {e.id: getattr(e, "nome", None) for e in getattr(entregador, "empresas", [])}

        logger.info(
            f"[EntregadoresService] Relatório detalhado - entregador_id={entregador_id}, "
            f"empresas={empresa_ids}, inicio={inicio}, fim={fim}"
        )

        base_filter = [
            PedidoUnificadoModel.empresa_id.in_(empresa_ids) if empresa_ids else False,
            PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
            PedidoUnificadoModel.entregador_id == entregador_id,
            PedidoUnificadoModel.created_at >= inicio,
            PedidoUnificadoModel.created_at < fim_exclusive,
        ]

        pedido_pago_expr = exists().where(
            and_(
                TransacaoPagamentoModel.pedido_id == PedidoUnificadoModel.id,
                TransacaoPagamentoModel.status.in_(("PAGO", "AUTORIZADO")),
            )
        )

        # agregados gerais
        total_row = (
            self.db.query(
                func.count(PedidoUnificadoModel.id).label("total_pedidos"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value, 1),
                        else_=0,
                    )
                ).label("total_pedidos_entregues"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.status == StatusPedido.CANCELADO.value, 1),
                        else_=0,
                    )
                ).label("total_pedidos_cancelados"),
                func.sum(
                    case(
                        (pedido_pago_expr, 1),
                        else_=0,
                    )
                ).label("total_pedidos_pagos"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor_total"),
                func.min(PedidoUnificadoModel.created_at).label("primeiro_pedido"),
                func.max(PedidoUnificadoModel.created_at).label("ultimo_pedido"),
            )
            .filter(*base_filter)
            .one()
        )

        total_pedidos = int(total_row.total_pedidos or 0)
        total_pedidos_entregues = int(total_row.total_pedidos_entregues or 0)
        total_pedidos_cancelados = int(total_row.total_pedidos_cancelados or 0)
        total_pedidos_pagos = int(total_row.total_pedidos_pagos or 0)
        valor_total = self._to_money(total_row.valor_total)

        dias_no_periodo = max((fim - inicio).days, 1)

        # pedidos por dia (criação)
        resumo_por_dia_rows: List[tuple] = (
            self.db.query(
                cast(PedidoUnificadoModel.created_at, Date).label("dia"),
                func.count(PedidoUnificadoModel.id).label("qtd"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor"),
            )
            .filter(*base_filter)
            .group_by(cast(PedidoUnificadoModel.created_at, Date))
            .order_by("dia")
            .all()
        )

        resumo_por_dia: List[EntregadorRelatorioDiaOut] = []
        for r in resumo_por_dia_rows:
            resumo_por_dia.append(
                EntregadorRelatorioDiaOut(
                    data=r.dia,
                    qtd_pedidos=int(r.qtd or 0),
                    valor_total=self._to_money(r.valor),
                )
            )

        dias_ativos = len(resumo_por_dia_rows)

        # acertos por dia (acertado_entregador_em) - geral (todas as empresas vinculadas)
        acertos_rows: List[tuple] = (
            self.db.query(
                cast(PedidoUnificadoModel.acertado_entregador_em, Date).label("dia"),
                func.count(PedidoUnificadoModel.id).label("qtd"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor"),
            )
            .filter(
                PedidoUnificadoModel.empresa_id.in_(empresa_ids) if empresa_ids else False,
                PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                PedidoUnificadoModel.entregador_id == entregador_id,
                PedidoUnificadoModel.acertado_entregador.is_(True),
                PedidoUnificadoModel.acertado_entregador_em >= inicio,
                PedidoUnificadoModel.acertado_entregador_em < fim_exclusive,
            )
            .group_by(cast(PedidoUnificadoModel.acertado_entregador_em, Date))
            .order_by("dia")
            .all()
        )

        resumo_acertos_por_dia: List[EntregadorRelatorioDiaAcertoOut] = []
        total_pedidos_acertados = 0
        total_valor_acertado_raw = 0.0
        for r in acertos_rows:
            qtd = int(r.qtd or 0)
            valor = self._to_money(r.valor)
            resumo_acertos_por_dia.append(
                EntregadorRelatorioDiaAcertoOut(
                    data=r.dia,
                    qtd_pedidos_acertados=qtd,
                    valor_total_acertado=valor,
                )
            )
            total_pedidos_acertados += qtd
            total_valor_acertado_raw += valor

        dias_acerto = max(len(acertos_rows), 1) if acertos_rows else 0

        # pendente de acerto: pedidos ENTREGUES ainda não acertados no período (geral)
        pendentes_row = (
            self.db.query(
                func.count(PedidoUnificadoModel.id).label("qtd"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor"),
            )
            .filter(
                *base_filter,
                PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value,
                PedidoUnificadoModel.acertado_entregador.is_(False),
            )
            .one()
        )
        total_pedidos_pendentes_acerto = int(pendentes_row.qtd or 0)
        total_valor_pendente_acerto = self._to_money(pendentes_row.valor)

        # tempo médio de entrega:
        # do momento em que o pedido muda para "Saiu para entrega" (S)
        # até o momento em que muda para "Entregue" (E), usando o histórico.
        pedidos_entregues = (
            self.db.query(PedidoUnificadoModel)
            .options(selectinload(PedidoUnificadoModel.historico))
            .filter(
                *base_filter,
                PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value,
            )
            .all()
        )

        tempo_medio_entrega_minutos = 0.0
        tempo_por_empresa: dict[int, dict[str, float]] = {}
        if pedidos_entregues:
            soma_segundos = 0.0
            validos = 0
            for pedido in pedidos_entregues:
                historico = getattr(pedido, "historico", []) or []

                ts_saiu = None
                ts_entregue = None

                for h in historico:
                    status_novo_val = (
                        h.status_novo.value
                        if hasattr(h.status_novo, "value")
                        else str(h.status_novo) if h.status_novo is not None
                        else None
                    )

                    if (
                        status_novo_val == StatusPedido.SAIU_PARA_ENTREGA.value
                        and ts_saiu is None
                    ):
                        ts_saiu = h.created_at
                    if (
                        status_novo_val == StatusPedido.ENTREGUE.value
                        and ts_entregue is None
                    ):
                        ts_entregue = h.created_at

                if ts_saiu and ts_entregue and isinstance(ts_entregue - ts_saiu, timedelta):
                    delta = ts_entregue - ts_saiu
                    soma_segundos += delta.total_seconds()
                    validos += 1

                    emp_id = getattr(pedido, "empresa_id", None)
                    if emp_id is not None:
                        agg = tempo_por_empresa.setdefault(emp_id, {"soma": 0.0, "qtd": 0})
                        agg["soma"] += delta.total_seconds()
                        agg["qtd"] += 1

            if validos > 0:
                tempo_medio_entrega_minutos = soma_segundos / validos / 60.0

        tempo_medio_por_empresa: dict[int, float] = {}
        for emp_id, data in tempo_por_empresa.items():
            if data["qtd"] > 0:
                tempo_medio_por_empresa[emp_id] = data["soma"] / data["qtd"] / 60.0

        ticket_medio = valor_total / total_pedidos if total_pedidos > 0 else 0.0
        ticket_medio_entregues = (
            valor_total / total_pedidos_entregues if total_pedidos_entregues > 0 else 0.0
        )

        pedidos_medio_por_dia = total_pedidos / dias_no_periodo if dias_no_periodo > 0 else 0.0
        valor_medio_por_dia = valor_total / dias_no_periodo if dias_no_periodo > 0 else 0.0

        media_pedidos_acertados_por_dia = (
            (total_pedidos_acertados / dias_acerto) if dias_acerto > 0 else 0.0
        )
        media_valor_acertado_por_dia = (
            (total_valor_acertado_raw / dias_acerto) if dias_acerto > 0 else 0.0
        )

        # ------------- métricas por empresa -------------
        # totais por empresa (pedidos, valores, dias ativos)
        stats_por_empresa_rows = (
            self.db.query(
                PedidoUnificadoModel.empresa_id.label("empresa_id"),
                func.count(PedidoUnificadoModel.id).label("total_pedidos"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value, 1),
                        else_=0,
                    )
                ).label("total_pedidos_entregues"),
                func.sum(
                    case(
                        (PedidoUnificadoModel.status == StatusPedido.CANCELADO.value, 1),
                        else_=0,
                    )
                ).label("total_pedidos_cancelados"),
                func.sum(
                    case(
                        (pedido_pago_expr, 1),
                        else_=0,
                    )
                ).label("total_pedidos_pagos"),
                func.sum(PedidoUnificadoModel.valor_total).label("valor_total"),
                func.count(
                    func.distinct(cast(PedidoUnificadoModel.created_at, Date))
                ).label("dias_ativos"),
            )
            .filter(*base_filter)
            .group_by(PedidoUnificadoModel.empresa_id)
            .all()
        )

        stats_map = {row.empresa_id: row for row in stats_por_empresa_rows}

        # acertos por empresa (totais e dias com acerto)
        # Usa apenas taxa_entrega para o cálculo de acerto
        acertos_por_empresa_rows = (
            self.db.query(
                PedidoUnificadoModel.empresa_id.label("empresa_id"),
                func.count(PedidoUnificadoModel.id).label("total_pedidos_acertados"),
                func.sum(PedidoUnificadoModel.taxa_entrega).label("total_valor_acertado"),
                func.count(
                    func.distinct(cast(PedidoUnificadoModel.acertado_entregador_em, Date))
                ).label("dias_acerto"),
            )
            .filter(
                PedidoUnificadoModel.empresa_id.in_(empresa_ids) if empresa_ids else False,
                PedidoUnificadoModel.tipo_entrega == TipoEntrega.DELIVERY.value,
                PedidoUnificadoModel.entregador_id == entregador_id,
                PedidoUnificadoModel.acertado_entregador.is_(True),
                PedidoUnificadoModel.acertado_entregador_em >= inicio,
                PedidoUnificadoModel.acertado_entregador_em < fim_exclusive,
            )
            .group_by(PedidoUnificadoModel.empresa_id)
            .all()
        )
        acertos_map = {row.empresa_id: row for row in acertos_por_empresa_rows}

        # pendentes por empresa
        # Usa apenas taxa_entrega para o cálculo de acerto
        pendentes_por_empresa_rows = (
            self.db.query(
                PedidoUnificadoModel.empresa_id.label("empresa_id"),
                func.count(PedidoUnificadoModel.id).label("qtd"),
                func.sum(PedidoUnificadoModel.taxa_entrega).label("valor"),
            )
            .filter(
                *base_filter,
                PedidoUnificadoModel.status == StatusPedido.ENTREGUE.value,
                PedidoUnificadoModel.acertado_entregador.is_(False),
            )
            .group_by(PedidoUnificadoModel.empresa_id)
            .all()
        )
        pendentes_map = {row.empresa_id: row for row in pendentes_por_empresa_rows}

        empresas_out: list[EntregadorRelatorioEmpresaOut] = []
        for emp_id in empresa_ids:
            stats = stats_map.get(emp_id)
            if not stats:
                continue

            total_pedidos_emp = int(stats.total_pedidos or 0)
            total_pedidos_entregues_emp = int(stats.total_pedidos_entregues or 0)
            total_pedidos_cancelados_emp = int(stats.total_pedidos_cancelados or 0)
            total_pedidos_pagos_emp = int(stats.total_pedidos_pagos or 0)
            valor_total_emp = self._to_money(stats.valor_total)
            dias_ativos_emp = int(stats.dias_ativos or 0)

            ticket_medio_emp = valor_total_emp / total_pedidos_emp if total_pedidos_emp > 0 else 0.0
            ticket_medio_entregues_emp = (
                valor_total_emp / total_pedidos_entregues_emp
                if total_pedidos_entregues_emp > 0
                else 0.0
            )

            pedidos_medio_por_dia_emp = (
                total_pedidos_emp / dias_ativos_emp if dias_ativos_emp > 0 else 0.0
            )
            valor_medio_por_dia_emp = (
                valor_total_emp / dias_ativos_emp if dias_ativos_emp > 0 else 0.0
            )

            acertos_emp = acertos_map.get(emp_id)
            if acertos_emp:
                total_pedidos_acertados_emp = int(acertos_emp.total_pedidos_acertados or 0)
                total_valor_acertado_emp = self._to_money(acertos_emp.total_valor_acertado)
                dias_acerto_emp = int(acertos_emp.dias_acerto or 0)
            else:
                total_pedidos_acertados_emp = 0
                total_valor_acertado_emp = 0.0
                dias_acerto_emp = 0

            media_pedidos_acertados_por_dia_emp = (
                total_pedidos_acertados_emp / dias_acerto_emp if dias_acerto_emp > 0 else 0.0
            )
            media_valor_acertado_por_dia_emp = (
                total_valor_acertado_emp / dias_acerto_emp if dias_acerto_emp > 0 else 0.0
            )

            pendentes_emp = pendentes_map.get(emp_id)
            if pendentes_emp:
                total_pedidos_pendentes_emp = int(pendentes_emp.qtd or 0)
                total_valor_pendente_emp = self._to_money(pendentes_emp.valor)
            else:
                total_pedidos_pendentes_emp = 0
                total_valor_pendente_emp = 0.0

            tempo_medio_emp = tempo_medio_por_empresa.get(emp_id, 0.0)

            empresas_out.append(
                EntregadorRelatorioEmpresaOut(
                    empresa_id=emp_id,
                    empresa_nome=empresa_nome_map.get(emp_id),
                    total_pedidos=total_pedidos_emp,
                    total_pedidos_entregues=total_pedidos_entregues_emp,
                    total_pedidos_cancelados=total_pedidos_cancelados_emp,
                    total_pedidos_pagos=total_pedidos_pagos_emp,
                    valor_total=valor_total_emp,
                    ticket_medio=ticket_medio_emp,
                    ticket_medio_entregues=ticket_medio_entregues_emp,
                    tempo_medio_entrega_minutos=tempo_medio_emp,
                    dias_ativos=dias_ativos_emp,
                    pedidos_medio_por_dia=pedidos_medio_por_dia_emp,
                    valor_medio_por_dia=valor_medio_por_dia_emp,
                    total_pedidos_acertados=total_pedidos_acertados_emp,
                    total_valor_acertado=total_valor_acertado_emp,
                    media_pedidos_acertados_por_dia=media_pedidos_acertados_por_dia_emp,
                    media_valor_acertado_por_dia=media_valor_acertado_por_dia_emp,
                    total_pedidos_pendentes_acerto=total_pedidos_pendentes_emp,
                    total_valor_pendente_acerto=total_valor_pendente_emp,
                )
            )

        return EntregadorRelatorioDetalhadoOut(
            entregador_id=entregador_id,
            entregador_nome=getattr(entregador, "nome", None),
            empresa_id=None,
            inicio=inicio,
            fim=fim,
            total_pedidos=total_pedidos,
            total_pedidos_entregues=total_pedidos_entregues,
            total_pedidos_cancelados=total_pedidos_cancelados,
            total_pedidos_pagos=total_pedidos_pagos,
            valor_total=valor_total,
            ticket_medio=ticket_medio,
            ticket_medio_entregues=ticket_medio_entregues,
            tempo_medio_entrega_minutos=tempo_medio_entrega_minutos,
            dias_no_periodo=dias_no_periodo,
            dias_ativos=dias_ativos,
            pedidos_medio_por_dia=pedidos_medio_por_dia,
            valor_medio_por_dia=valor_medio_por_dia,
            total_pedidos_acertados=total_pedidos_acertados,
            total_valor_acertado=total_valor_acertado_raw,
            media_pedidos_acertados_por_dia=media_pedidos_acertados_por_dia,
            media_valor_acertado_por_dia=media_valor_acertado_por_dia,
            total_pedidos_pendentes_acerto=total_pedidos_pendentes_acerto,
            total_valor_pendente_acerto=total_valor_pendente_acerto,
            resumo_por_dia=resumo_por_dia,
            resumo_acertos_por_dia=resumo_acertos_por_dia,
            empresas=empresas_out,
        )

