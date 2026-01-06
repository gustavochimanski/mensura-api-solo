from __future__ import annotations

from typing import List
from sqlalchemy.orm import Session, joinedload

from app.api.cardapio.repositories.repo_printer import PrinterRepository
from app.api.cardapio.schemas.schema_printer import (
    DadosEmpresaPrinter,
    ItemPedidoPrinter,
    PedidoPendenteImpressaoResponse,
    PedidosPendentesPrinterResponse,
    RespostaImpressaoPrinter,
    TipoPedidoPrinterEnum,
)
from app.api.pedidos.models.model_pedido_unificado import PedidoUnificadoModel, TipoEntrega, StatusPedido
from app.api.pedidos.utils.produtos_builder import build_produtos_out_from_items
from sqlalchemy import and_
from datetime import datetime, timedelta
from app.utils.logger import logger


class PrinterService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PrinterRepository(db)

    STATUS_IMPRESSAO = "I"
    MESA_STATUS_PENDENTES = {StatusPedido.IMPRESSAO.value}
    BALCAO_STATUS_PENDENTES = {StatusPedido.IMPRESSAO.value}

    def get_pedidos_pendentes_para_impressao(
        self,
        empresa_id: int,
        limite: int | None = None,
    ) -> PedidosPendentesPrinterResponse:
        """
        Retorna os pedidos pendentes de impressão agrupados por canal (delivery, mesa e balcão).
        """
        pedidos_delivery = self.repo.get_pedidos_pendentes_impressao(empresa_id=empresa_id, limite=limite)
        delivery = [self._converter_pedido_delivery(p) for p in pedidos_delivery]

        mesa = self._listar_pedidos_mesa_pendentes(empresa_id=empresa_id, limite=limite)
        balcao = self._listar_pedidos_balcao_pendentes(empresa_id=empresa_id, limite=limite)

        return PedidosPendentesPrinterResponse(
            delivery=delivery,
            mesa=mesa,
            balcao=balcao,
        )

    # ------------------------------------------------------------------
    # Conversões / Helpers
    # ------------------------------------------------------------------
    def _converter_pedido_delivery(self, pedido) -> PedidoPendenteImpressaoResponse:
        produtos = build_produtos_out_from_items(pedido.itens)
        endereco = self._montar_endereco_delivery(pedido)

        troco = None
        troco_para = getattr(pedido, "troco_para", None)
        if troco_para:
            try:
                troco_calculado = float(troco_para or 0) - float(pedido.valor_total or 0)
                if troco_calculado > 0:
                    troco = troco_calculado
            except Exception:
                troco = None

        return PedidoPendenteImpressaoResponse(
            numero=pedido.id,
            status=self._status_to_str(pedido.status),
            cliente=pedido.cliente.nome if pedido.cliente else "Cliente não informado",
            telefone_cliente=pedido.cliente.telefone if pedido.cliente else None,
            produtos=produtos,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            total=float(pedido.valor_total or 0),
            tipo_pagamento=pedido.meio_pagamento.display() if pedido.meio_pagamento else "Não informado",
            troco=troco,
            observacao_geral=pedido.observacao_geral,
            endereco=endereco,
            data_criacao=pedido.created_at,
            empresa=self._build_empresa_data(pedido.empresa),
            tipo_pedido=TipoPedidoPrinterEnum.DELIVERY,
        )

    def _listar_pedidos_mesa_pendentes(
        self,
        *,
        empresa_id: int,
        limite: int | None,
    ) -> List[PedidoPendenteImpressaoResponse]:
        """Lista pedidos de mesa pendentes de impressão usando modelo unificado."""
        try:
            query = (
                self.db.query(PedidoUnificadoModel)
                .options(
                    joinedload(PedidoUnificadoModel.itens),
                    joinedload(PedidoUnificadoModel.cliente),
                    joinedload(PedidoUnificadoModel.mesa),
                    joinedload(PedidoUnificadoModel.empresa),
                    joinedload(PedidoUnificadoModel.meio_pagamento),
                )
                .filter(
                    and_(
                        PedidoUnificadoModel.empresa_id == empresa_id,
                        PedidoUnificadoModel.tipo_entrega == TipoEntrega.MESA.value,
                        PedidoUnificadoModel.status == StatusPedido.IMPRESSAO.value,
                    )
                )
                .order_by(PedidoUnificadoModel.created_at.asc())
            )
            if limite:
                query = query.limit(limite)
            pedidos = query.all()
            return [self._converter_pedido_mesa_unificado(p) for p in pedidos]
        except Exception as exc:
            logger.warning(f"[Printer] Falha ao buscar pedidos de mesa pendentes: {exc}")
            return []

    def _listar_pedidos_balcao_pendentes(
        self,
        *,
        empresa_id: int,
        limite: int | None,
    ) -> List[PedidoPendenteImpressaoResponse]:
        """Lista pedidos de balcão pendentes de impressão usando modelo unificado."""
        try:
            query = (
                self.db.query(PedidoUnificadoModel)
                .options(
                    joinedload(PedidoUnificadoModel.itens),
                    joinedload(PedidoUnificadoModel.cliente),
                    joinedload(PedidoUnificadoModel.mesa),
                    joinedload(PedidoUnificadoModel.empresa),
                    joinedload(PedidoUnificadoModel.meio_pagamento),
                )
                .filter(
                    and_(
                        PedidoUnificadoModel.empresa_id == empresa_id,
                        PedidoUnificadoModel.tipo_entrega == TipoEntrega.BALCAO.value,
                        PedidoUnificadoModel.status == StatusPedido.IMPRESSAO.value,
                    )
                )
                .order_by(PedidoUnificadoModel.created_at.asc())
            )
            if limite:
                query = query.limit(limite)
            pedidos = query.all()
            return [self._converter_pedido_balcao_unificado(p) for p in pedidos]
        except Exception as exc:
            logger.warning(f"[Printer] Falha ao buscar pedidos de balcão pendentes: {exc}")
            return []

    def _converter_pedido_mesa_unificado(self, pedido: PedidoUnificadoModel) -> PedidoPendenteImpressaoResponse:
        produtos = build_produtos_out_from_items(pedido.itens)
        subtotal = self._calcular_subtotal_db_items(pedido.itens, pedido.valor_total)

        observacao = pedido.observacoes or pedido.observacao_geral or ""
        if pedido.numero_pedido:
            observacao = (
                f"{pedido.numero_pedido}" + (f" - {observacao}" if observacao else "")
            )

        endereco = None
        if pedido.mesa and getattr(pedido.mesa, "numero", None):
            endereco = f"Mesa {pedido.mesa.numero}"

        return PedidoPendenteImpressaoResponse(
            numero=pedido.id,
            status=self._status_to_str(pedido.status),
            cliente=pedido.cliente.nome if pedido.cliente else "Cliente",
            telefone_cliente=pedido.cliente.telefone if pedido.cliente else None,
            produtos=produtos,
            subtotal=subtotal,
            desconto=0.0,
            taxa_entrega=0.0,
            taxa_servico=0.0,
            total=float(pedido.valor_total or subtotal),
            tipo_pagamento=pedido.meio_pagamento.display() if pedido.meio_pagamento else "Mesa",
            troco=float(pedido.troco_para) if getattr(pedido, "troco_para", None) is not None else None,
            observacao_geral=observacao or None,
            endereco=endereco,
            data_criacao=pedido.created_at,
            empresa=self._build_empresa_data(pedido.empresa),
            tipo_pedido=TipoPedidoPrinterEnum.MESA,
        )

    def _converter_pedido_balcao_unificado(self, pedido: PedidoUnificadoModel) -> PedidoPendenteImpressaoResponse:
        produtos = build_produtos_out_from_items(pedido.itens)
        subtotal = self._calcular_subtotal_db_items(pedido.itens, pedido.valor_total)

        observacao = pedido.observacoes or pedido.observacao_geral or ""
        if pedido.numero_pedido:
            observacao = (
                f"{pedido.numero_pedido}" + (f" - {observacao}" if observacao else "")
            )

        if pedido.mesa and getattr(pedido.mesa, "numero", None):
            endereco = f"Mesa {pedido.mesa.numero} (Balcão)"
        else:
            endereco = "Retirada no balcão"

        troco = None
        troco_para = getattr(pedido, "troco_para", None)
        if troco_para:
            try:
                troco_calculado = float(troco_para or 0) - float(pedido.valor_total or 0)
                if troco_calculado > 0:
                    troco = troco_calculado
            except Exception:
                troco = None

        return PedidoPendenteImpressaoResponse(
            numero=pedido.id,
            status=self._status_to_str(pedido.status),
            cliente=pedido.cliente.nome if pedido.cliente else "Cliente",
            telefone_cliente=pedido.cliente.telefone if pedido.cliente else None,
            produtos=produtos,
            subtotal=subtotal,
            desconto=0.0,
            taxa_entrega=0.0,
            taxa_servico=0.0,
            total=float(pedido.valor_total or subtotal),
            tipo_pagamento=pedido.meio_pagamento.display() if pedido.meio_pagamento else "Balcão",
            troco=troco,
            observacao_geral=observacao or None,
            endereco=endereco,
            data_criacao=pedido.created_at,
            empresa=self._build_empresa_data(pedido.empresa),
            tipo_pedido=TipoPedidoPrinterEnum.BALCAO,
        )

    def _converter_itens(self, itens) -> List[ItemPedidoPrinter]:
        resultado: List[ItemPedidoPrinter] = []
        for item in itens or []:
            descricao = (
                getattr(item, "produto_descricao_snapshot", None)
                or getattr(item, "descricao", None)
                or f"Produto {getattr(item, 'produto_cod_barras', '')}".strip()
            )
            quantidade = int(getattr(item, "quantidade", 0) or 0)
            preco = float(getattr(item, "preco_unitario", 0) or 0)
            observacao = getattr(item, "observacao", None)

            resultado.append(
                ItemPedidoPrinter(
                    descricao=descricao,
                    quantidade=quantidade,
                    preco=preco,
                    observacao=observacao,
                )
            )
        return resultado

    @staticmethod
    def _status_to_str(status) -> str:
        if status is None:
            return ""
        if isinstance(status, str):
            return status
        return getattr(status, "value", str(status))

    @staticmethod
    def _calcular_subtotal(itens: List[ItemPedidoPrinter], valor_total) -> float:
        subtotal = sum(item.preco * item.quantidade for item in itens)
        if subtotal == 0 and valor_total is not None:
            try:
                subtotal = float(valor_total)
            except Exception:
                subtotal = 0.0
        return float(subtotal)

    @staticmethod
    def _calcular_subtotal_db_items(itens_db, valor_total) -> float:
        subtotal = 0.0
        for item in itens_db or []:
            try:
                qtd = int(getattr(item, "quantidade", 0) or 0)
                preco_unit = float(getattr(item, "preco_unitario", 0) or 0)
                subtotal += preco_unit * qtd
            except Exception:
                continue
        if subtotal == 0 and valor_total is not None:
            try:
                subtotal = float(valor_total)
            except Exception:
                subtotal = 0.0
        return float(subtotal)

    @staticmethod
    def _build_empresa_data(empresa) -> DadosEmpresaPrinter:
        if not empresa:
            return DadosEmpresaPrinter(cnpj=None, endereco=None, telefone=None)
        return DadosEmpresaPrinter(
            cnpj=getattr(empresa, "cnpj", None),
            endereco=None,
            telefone=getattr(empresa, "telefone", None),
        )

    @staticmethod
    def _montar_endereco_delivery(pedido) -> str | None:
        snapshot = getattr(pedido, "endereco_snapshot", None)
        if snapshot:
            return ", ".join(
                filter(
                    None,
                    [
                        snapshot.get("logradouro"),
                        snapshot.get("numero"),
                        snapshot.get("bairro"),
                        snapshot.get("cidade"),
                        snapshot.get("cep"),
                        snapshot.get("complemento"),
                    ],
                )
            )

        cliente = getattr(pedido, "cliente", None)
        if cliente:
            enderecos = getattr(cliente, "enderecos", None) or []
            if enderecos:
                endereco_model = enderecos[0]
                return ", ".join(
                    filter(
                        None,
                        [
                            getattr(endereco_model, "logradouro", None),
                            getattr(endereco_model, "numero", None),
                            getattr(endereco_model, "bairro", None),
                            getattr(endereco_model, "cidade", None),
                            getattr(endereco_model, "cep", None),
                            getattr(endereco_model, "complemento", None),
                        ],
                    )
                )
        return None

    def marcar_pedido_impresso_manual(
        self,
        pedido_id: int,
        tipo_pedido: TipoPedidoPrinterEnum,
    ) -> RespostaImpressaoPrinter:
        ok = self.repo.marcar_pedido_impresso(pedido_id, tipo_pedido)
        if ok:
            return RespostaImpressaoPrinter(
                sucesso=True,
                mensagem=f"Pedido {pedido_id} ({tipo_pedido.value}) marcado como impresso",
                numero_pedido=pedido_id,
            )
        return RespostaImpressaoPrinter(
            sucesso=False,
            mensagem=f"Não foi possível marcar o pedido {pedido_id} ({tipo_pedido.value}) como impresso",
            numero_pedido=pedido_id,
        )

    def get_estatisticas_impressao(self, empresa_id: int) -> dict:
        return self.repo.get_estatisticas_impressao(empresa_id)


