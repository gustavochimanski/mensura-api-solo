from __future__ import annotations

from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.financeiro.schemas.schema_acerto_motoboy import (
    PedidoPendenteAcertoOut,
    FecharPedidosDiretoRequest,
    FecharPedidosDiretoResponse,
    PreviewAcertoResponse,
    ResumoAcertoEntregador,
    AcertosPassadosResponse,
)
from app.api.cardapio.models.model_pedido_dv import PedidoDeliveryModel
from app.api.cadastros.models.model_entregador_dv import EntregadorDeliveryModel
from decimal import Decimal
from app.utils.database_utils import now_trimmed


class AcertoEntregadoresService:
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_money(value) -> float:
        """Converte para float com 2 casas, evitando issues de precisão/strings."""
        if value is None:
            return 0.0
        if not isinstance(value, Decimal):
            try:
                value = Decimal(str(value))
            except Exception:
                return 0.0
        return float(value.quantize(Decimal("0.01")))

    def _normalize_period(self, inicio, fim):
        from datetime import timedelta
        # Usa limite superior exclusivo para evitar problemas de microsegundos
        # Se 'fim' vier como data exata (sem horário), considere o dia inteiro
        fim_exclusive = fim
        if getattr(fim, "hour", 0) == 0 and getattr(fim, "minute", 0) == 0 and getattr(fim, "second", 0) == 0 and getattr(fim, "microsecond", 0) == 0:
            fim_exclusive = fim + timedelta(days=1)
        else:
            fim_exclusive = fim + timedelta(microseconds=1)
        return inicio, fim_exclusive

    def listar_pendentes(self, *, empresa_id: int, inicio, fim, entregador_id: int | None = None) -> list[PedidoPendenteAcertoOut]:
        inicio, fim_exclusive = self._normalize_period(inicio, fim)
        q = (
            self.db.query(PedidoDeliveryModel)
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.entregador_id.isnot(None),
                PedidoDeliveryModel.status == "E",
                PedidoDeliveryModel.acertado_entregador == False,
                PedidoDeliveryModel.data_criacao >= inicio,
                PedidoDeliveryModel.data_criacao < fim_exclusive,
            )
        )
        if entregador_id is not None:
            q = q.filter(PedidoDeliveryModel.entregador_id == entregador_id)
        pedidos = q.order_by(PedidoDeliveryModel.data_criacao.asc()).all()
        return [PedidoPendenteAcertoOut.model_validate(p) for p in pedidos]

    # --------- Fechamento direto (sem criar acerto) ---------
    def fechar_pedidos_direto(self, payload: FecharPedidosDiretoRequest) -> FecharPedidosDiretoResponse:
        empresa_id = payload.empresa_id
        inicio = payload.inicio
        fim = payload.fim
        entregador_id = payload.entregador_id

        inicio, fim_exclusive = self._normalize_period(inicio, fim)

        # Seleciona os pedidos via ORM
        q = (
            self.db.query(PedidoDeliveryModel)
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.entregador_id.isnot(None),
                PedidoDeliveryModel.status == "E",
                PedidoDeliveryModel.acertado_entregador == False,
                PedidoDeliveryModel.data_criacao >= inicio,
                PedidoDeliveryModel.data_criacao < fim_exclusive,
            )
        )
        if entregador_id is not None:
            q = q.filter(PedidoDeliveryModel.entregador_id == entregador_id)
        pedidos = q.all()

        if not pedidos:
            return FecharPedidosDiretoResponse(
                pedidos_fechados=0,
                pedido_ids=[],
                valor_total=0,
                inicio=inicio,
                fim=fim,
                mensagem="Nenhum pedido encontrado para o período.",
            )

        # Atualiza via ORM e calcula total
        total_dec = Decimal("0")
        total_diarias = Decimal("0")
        ids = []
        now = now_trimmed()
        for p in pedidos:
            ids.append(p.id)
            p.acertado_entregador = True
            p.acertado_entregador_em = now
            p.data_atualizacao = now
            try:
                if p.valor_total is not None:
                    total_dec += Decimal(p.valor_total)
            except Exception:
                pass

        # Diária por entregador (se entregador_id definido, usa a do entregador; caso contrário soma por entregadores distintos no período)
        if entregador_id is not None:
            ent = self.db.query(EntregadorDeliveryModel).filter(EntregadorDeliveryModel.id == entregador_id).first()
            if ent and getattr(ent, "valor_diaria", None) is not None:
                try:
                    total_diarias += Decimal(ent.valor_diaria)
                except Exception:
                    pass
        else:
            ent_ids = set(p.entregador_id for p in pedidos if p.entregador_id)
            if ent_ids:
                entregadores = (
                    self.db.query(EntregadorDeliveryModel)
                    .filter(EntregadorDeliveryModel.id.in_(list(ent_ids)))
                    .all()
                )
                for ent in entregadores:
                    if getattr(ent, "valor_diaria", None) is not None:
                        try:
                            total_diarias += Decimal(ent.valor_diaria)
                        except Exception:
                            pass

        self.db.commit()

        return FecharPedidosDiretoResponse(
            pedidos_fechados=len(ids),
            pedido_ids=ids,
            valor_total=self._to_money(total_dec),
            valor_diaria_total=self._to_money(total_diarias),
            valor_liquido=self._to_money((total_dec + total_diarias) if (total_dec is not None and total_diarias is not None) else 0),
            inicio=inicio,
            fim=fim,
            mensagem=f"Pedidos marcados como acertados por {payload.fechado_por}" if payload.fechado_por else None,
        )

    # --------- Preview (dados necessários para acerto) ---------
    def preview_acerto(self, *, empresa_id: int, inicio, fim, entregador_id: int | None = None) -> PreviewAcertoResponse:
        inicio, fim_exclusive = self._normalize_period(inicio, fim)
        q = (
            self.db.query(PedidoDeliveryModel)
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.entregador_id.isnot(None),
                PedidoDeliveryModel.status == "E",
                PedidoDeliveryModel.acertado_entregador == False,
                PedidoDeliveryModel.data_criacao >= inicio,
                PedidoDeliveryModel.data_criacao < fim_exclusive,
            )
        )
        if entregador_id is not None:
            q = q.filter(PedidoDeliveryModel.entregador_id == entregador_id)
        pedidos = q.all()

        # Agrupar por entregador e por dia (data de criação do pedido)
        entregador_dia_to_sum = {}
        for p in pedidos:
            ent_id = p.entregador_id
            if not ent_id:
                continue
            try:
                dia = p.data_criacao.date()
            except Exception:
                # fallback: sem data, ignora
                continue
            key = (ent_id, dia)
            entry = entregador_dia_to_sum.setdefault(key, {"qtd": 0, "total": Decimal("0")})
            entry["qtd"] += 1
            try:
                if p.valor_total is not None:
                    entry["total"] += Decimal(p.valor_total)
            except Exception:
                pass

        resumos: list[ResumoAcertoEntregador] = []
        total_pedidos = 0
        total_bruto = Decimal("0")
        total_diarias = Decimal("0")
        total_liquido = Decimal("0")

        if entregador_dia_to_sum:
            ent_ids = list({ent_id for (ent_id, _dia) in entregador_dia_to_sum.keys()})
            entregadores = (
                self.db.query(EntregadorDeliveryModel)
                .filter(EntregadorDeliveryModel.id.in_(ent_ids))
                .all()
            )
            ent_map = {e.id: e for e in entregadores}
            # Emitir um resumo por (entregador, dia)
            for (ent_id, dia), sums in sorted(entregador_dia_to_sum.items(), key=lambda x: (x[0][0], x[0][1])):
                ent = ent_map.get(ent_id)
                diaria = Decimal(str(getattr(ent, "valor_diaria", 0) or 0)) if ent else Decimal("0")
                qtd = int(sums["qtd"])
                bruto = sums["total"]
                liquido = bruto + diaria
                resumos.append(
                    ResumoAcertoEntregador(
                        data=dia,
                        entregador_id=ent_id,
                        entregador_nome=(ent.nome if ent else None),
                        valor_diaria=self._to_money(diaria),
                        qtd_pedidos=qtd,
                        valor_pedidos=self._to_money(bruto),
                        valor_liquido=self._to_money(liquido),
                    )
                )
                total_pedidos += qtd
                total_bruto += bruto
                total_diarias += diaria
                total_liquido += liquido

        return PreviewAcertoResponse(
            empresa_id=empresa_id,
            inicio=inicio,
            fim=fim,
            entregador_id=entregador_id,
            resumos=resumos,
            total_pedidos=total_pedidos,
            total_bruto=self._to_money(total_bruto),
            total_diarias=self._to_money(total_diarias),
            total_liquido=self._to_money(total_liquido),
        )

    # --------- Acertos passados (já acertados) ---------
    def acertos_passados(self, *, empresa_id: int, inicio, fim, entregador_id: int | None = None) -> AcertosPassadosResponse:
        inicio, fim_exclusive = self._normalize_period(inicio, fim)
        q = (
            self.db.query(PedidoDeliveryModel)
            .filter(
                PedidoDeliveryModel.empresa_id == empresa_id,
                PedidoDeliveryModel.entregador_id.isnot(None),
                PedidoDeliveryModel.acertado_entregador == True,
                PedidoDeliveryModel.acertado_entregador_em >= inicio,
                PedidoDeliveryModel.acertado_entregador_em < fim_exclusive,
            )
        )
        if entregador_id is not None:
            q = q.filter(PedidoDeliveryModel.entregador_id == entregador_id)
        pedidos = q.all()

        # Agrupar por entregador e por dia (data de criação do pedido)
        entregador_dia_to_sum = {}
        for p in pedidos:
            ent_id = p.entregador_id
            if not ent_id:
                continue
            try:
                dia = p.data_criacao.date()
            except Exception:
                continue
            key = (ent_id, dia)
            entry = entregador_dia_to_sum.setdefault(key, {"qtd": 0, "total": Decimal("0")})
            entry["qtd"] += 1
            try:
                if p.valor_total is not None:
                    entry["total"] += Decimal(p.valor_total)
            except Exception:
                pass

        resumos: list[ResumoAcertoEntregador] = []
        total_pedidos = 0
        total_bruto = Decimal("0")
        total_diarias = Decimal("0")
        total_liquido = Decimal("0")

        if entregador_dia_to_sum:
            ent_ids = list({ent_id for (ent_id, _dia) in entregador_dia_to_sum.keys()})
            entregadores = (
                self.db.query(EntregadorDeliveryModel)
                .filter(EntregadorDeliveryModel.id.in_(ent_ids))
                .all()
            )
            ent_map = {e.id: e for e in entregadores}
            for (ent_id, dia), sums in sorted(entregador_dia_to_sum.items(), key=lambda x: (x[0][0], x[0][1])):
                ent = ent_map.get(ent_id)
                diaria = Decimal(str(getattr(ent, "valor_diaria", 0) or 0)) if ent else Decimal("0")
                qtd = int(sums["qtd"])
                bruto = sums["total"]
                liquido = bruto + diaria
                resumos.append(
                    ResumoAcertoEntregador(
                        data=dia,
                        entregador_id=ent_id,
                        entregador_nome=(ent.nome if ent else None),
                        valor_diaria=self._to_money(diaria),
                        qtd_pedidos=qtd,
                        valor_pedidos=self._to_money(bruto),
                        valor_liquido=self._to_money(liquido),
                    )
                )
                total_pedidos += qtd
                total_bruto += bruto
                total_diarias += diaria
                total_liquido += liquido

        return AcertosPassadosResponse(
            empresa_id=empresa_id,
            inicio=inicio,
            fim=fim,
            entregador_id=entregador_id,
            resumos=resumos,
            total_pedidos=total_pedidos,
            total_bruto=self._to_money(total_bruto),
            total_diarias=self._to_money(total_diarias),
            total_liquido=self._to_money(total_liquido),
        )


