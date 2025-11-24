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
# TODO: Migrar para modelos unificados (PedidoUnificadoModel)
# Temporariamente desabilitado - módulos mesas e balcao não existem mais
# Criando stubs para permitir que o código funcione
class StatusPedidoMesa:
    IMPRESSAO = type('Enum', (), {'value': 'I'})()

class StatusPedidoBalcao:
    IMPRESSAO = type('Enum', (), {'value': 'I'})()

# Stubs vazios - as funções retornarão listas vazias
PedidoMesaModel = None
PedidoBalcaoModel = None
from app.utils.logger import logger


class PrinterService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PrinterRepository(db)

    STATUS_IMPRESSAO = "I"
    MESA_STATUS_PENDENTES = {StatusPedidoMesa.IMPRESSAO.value}
    BALCAO_STATUS_PENDENTES = {StatusPedidoBalcao.IMPRESSAO.value}

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
        itens = self._converter_itens(pedido.itens)
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
            itens=itens,
            subtotal=float(pedido.subtotal or 0),
            desconto=float(pedido.desconto or 0),
            taxa_entrega=float(pedido.taxa_entrega or 0),
            taxa_servico=float(pedido.taxa_servico or 0),
            total=float(pedido.valor_total or 0),
            tipo_pagamento=pedido.meio_pagamento.display() if pedido.meio_pagamento else "Não informado",
            troco=troco,
            observacao_geral=pedido.observacao_geral,
            endereco=endereco,
            data_criacao=pedido.data_criacao,
            empresa=self._build_empresa_data(pedido.empresa),
            tipo_pedido=TipoPedidoPrinterEnum.DELIVERY,
        )

    def _listar_pedidos_mesa_pendentes(
        self,
        *,
        empresa_id: int,
        limite: int | None,
    ) -> List[PedidoPendenteImpressaoResponse]:
        # TODO: Migrar para usar PedidoUnificadoModel com tipo_pedido='MESA'
        # Temporariamente retorna lista vazia até migração completa
        logger.warning("[Printer] Funcionalidade de pedidos de mesa temporariamente desabilitada - aguardando migração para modelos unificados")
        return []

    def _listar_pedidos_balcao_pendentes(
        self,
        *,
        empresa_id: int,
        limite: int | None,
    ) -> List[PedidoPendenteImpressaoResponse]:
        # TODO: Migrar para usar PedidoUnificadoModel com tipo_pedido='BALCAO'
        # Temporariamente retorna lista vazia até migração completa
        logger.warning("[Printer] Funcionalidade de pedidos de balcão temporariamente desabilitada - aguardando migração para modelos unificados")
        return []

    def _converter_pedido_mesa(self, pedido: PedidoMesaModel) -> PedidoPendenteImpressaoResponse:
        itens = self._converter_itens(pedido.itens)
        subtotal = self._calcular_subtotal(itens, pedido.valor_total)

        observacao = pedido.observacoes or ""
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
            itens=itens,
            subtotal=subtotal,
            desconto=0.0,
            taxa_entrega=0.0,
            taxa_servico=0.0,
            total=float(pedido.valor_total or subtotal),
            tipo_pagamento="Mesa",
            troco=None,
            observacao_geral=observacao or None,
            endereco=endereco,
            data_criacao=pedido.created_at,
            empresa=self._build_empresa_data(pedido.empresa),
            tipo_pedido=TipoPedidoPrinterEnum.MESA,
        )

    def _converter_pedido_balcao(self, pedido: PedidoBalcaoModel) -> PedidoPendenteImpressaoResponse:
        itens = self._converter_itens(pedido.itens)
        subtotal = self._calcular_subtotal(itens, pedido.valor_total)

        observacao = pedido.observacoes or ""
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
            itens=itens,
            subtotal=subtotal,
            desconto=0.0,
            taxa_entrega=0.0,
            taxa_servico=0.0,
            total=float(pedido.valor_total or subtotal),
            tipo_pagamento="Balcão",
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


