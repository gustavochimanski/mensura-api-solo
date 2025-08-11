from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.delivery.repositories.pedidos_dv_repo import PedidoRepository
from app.api.mensura.repositories.empresa_repo import EmpresaRepository
from app.api.delivery.schemas.pedido_dv_schema import FinalizarPedidoRequest, ItemPedidoRequest, PedidoResponse, ItemPedidoResponse
from app.api.delivery.schemas.shared_enums import (
    PedidoStatusEnum, TipoEntregaEnum, OrigemPedidoEnum,
    PagamentoMetodoEnum, PagamentoGatewayEnum, PagamentoStatusEnum
)
from app.api.delivery.services.pagamento_gateway_service import PaymentGatewayClient

QTD_MAX_ITENS = 200  # proteção simples

def _dec(value: float | Decimal | int) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class PedidoService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = PedidoRepository(db)
        self.repo_empresa = EmpresaRepository(db)
        self.gateway = PaymentGatewayClient()  # usa MOCK por padrão

    # --------- Helpers de negócio ----------
    def _calcular_taxas(
        self, *, tipo_entrega: TipoEntregaEnum, subtotal: Decimal
    ) -> tuple[Decimal, Decimal]:
        taxa_entrega = _dec(8.90) if tipo_entrega == TipoEntregaEnum.DELIVERY else _dec(0)
        taxa_servico = (subtotal * Decimal("0.05")).quantize(Decimal("0.01"))  # 5%
        return taxa_entrega, taxa_servico

    def _aplicar_cupom(
        self, *, cupom_id: Optional[int], subtotal: Decimal
    ) -> Decimal:
        if not cupom_id:
            return _dec(0)
        cupom = self.repo.get_cupom(cupom_id)
        if not cupom or not cupom.ativo:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom inválido ou inativo")

        # validade e mínimo
        if cupom.validade_inicio and cupom.validade_fim:
            from datetime import datetime, timezone
            now = datetime.now(tz=timezone.utc)
            if not (cupom.validade_inicio <= now <= cupom.validade_fim):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cupom fora do período de validade")

        if cupom.minimo_compra and subtotal < cupom.minimo_compra:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Subtotal abaixo do mínimo para o cupom")

        desconto = Decimal("0")
        if cupom.desconto_valor:
            desconto += _dec(cupom.desconto_valor)
        if cupom.desconto_percentual:
            desconto += (subtotal * (Decimal(cupom.desconto_percentual) / Decimal("100"))).quantize(Decimal("0.01"))

        # não permitir desconto maior que subtotal
        if desconto > subtotal:
            desconto = subtotal
        return desconto

    # --------- Fluxo 1: criar pedido + itens + totais (status P) ----------
    def finalizar_pedido(self, payload: FinalizarPedidoRequest) -> PedidoResponse:
        if not payload.itens:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pedido vazio")
        if len(payload.itens) > QTD_MAX_ITENS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Itens demais no pedido")

        empresa = self.repo_empresa.get_empresa_by_id(payload.empresa_id)
        if not empresa:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa não encontrada")

        # validações de cliente/endereço
        if payload.cliente_id:
            cliente = self.repo.get_cliente(payload.cliente_id)
            if not cliente:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente não encontrado")

            if payload.tipo_entrega == TipoEntregaEnum.DELIVERY and not payload.endereco_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço é obrigatório para delivery")

            if payload.endereco_id:
                endereco = self.repo.get_endereco(payload.endereco_id)
                if not endereco or endereco.cliente_id != payload.cliente_id:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Endereço inválido para o cliente")

        try:
            # COMMIT atômico
            pedido = self.repo.criar_pedido(
                cliente_id=payload.cliente_id,
                empresa_id=payload.empresa_id,
                endereco_id=payload.endereco_id,
                status=PedidoStatusEnum.P.value,  # "P"
                tipo_entrega=payload.tipo_entrega.value,
                origem=payload.origem.value,
            )

            subtotal = Decimal("0")

            for it in payload.itens:
                pe = self.repo.get_produto_emp(payload.empresa_id, it.produto_cod_barras)
                if not pe:
                    raise HTTPException(status.HTTP_404_NOT_FOUND, f"Produto {it.produto_cod_barras} não encontrado")
                if not pe.disponivel or not (pe.produto and pe.produto.ativo):
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Produto indisponível: {it.produto_cod_barras}")

                preco = _dec(pe.preco_venda)
                subtotal += preco * it.quantidade

                self.repo.adicionar_item(
                    pedido_id=pedido.id,
                    cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=preco,
                    observacao=it.observacao,
                    produto_descricao_snapshot=pe.produto.descricao if pe.produto else None,
                    produto_imagem_snapshot=pe.produto.imagem if pe.produto else None,
                )

            desconto = self._aplicar_cupom(cupom_id=payload.cupom_id, subtotal=subtotal)
            taxa_entrega, taxa_servico = self._calcular_taxas(
                tipo_entrega=payload.tipo_entrega, subtotal=subtotal
            )

            self.repo.atualizar_totais(
                pedido,
                subtotal=subtotal,
                desconto=desconto,
                taxa_entrega=taxa_entrega,
                taxa_servico=taxa_servico,
            )

            # observações gerais / troco
            pedido.observacao_geral = payload.observacao_geral
            if payload.troco_para:
                pedido.troco_para = _dec(payload.troco_para)

            self.repo.commit()
            # refresh para popular itens/totais
            self.db.refresh(pedido)

        except HTTPException:
            self.repo.rollback()
            raise
        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao finalizar pedido: {e}")

        # monta response
        return PedidoResponse(
            id=pedido.id,
            status=PedidoStatusEnum(pedido.status),
            cliente_id=pedido.cliente_id,
            empresa_id=pedido.empresa_id,
            entregador_id=pedido.entregador_id,
            endereco_id=pedido.endereco_id,
            tipo_entrega=pedido.tipo_entrega,
            origem=pedido.origem,
            subtotal=float(pedido.subtotal),
            desconto=float(pedido.desconto),
            taxa_entrega=float(pedido.taxa_entrega),
            taxa_servico=float(pedido.taxa_servico),
            valor_total=float(pedido.valor_total),
            previsao_entrega=pedido.previsao_entrega,
            distancia_km=float(pedido.distancia_km) if pedido.distancia_km else None,
            observacao_geral=pedido.observacao_geral,
            troco_para=float(pedido.troco_para) if pedido.troco_para else None,
            cupom_id=pedido.cupom_id,
            data_criacao=pedido.data_criacao,
            data_atualizacao=pedido.data_atualizacao,
            itens=[
                ItemPedidoResponse(
                    id=it.id,
                    produto_cod_barras=it.produto_cod_barras,
                    quantidade=it.quantidade,
                    preco_unitario=float(it.preco_unitario),
                    observacao=it.observacao,
                    produto_descricao_snapshot=it.produto_descricao_snapshot,
                    produto_imagem_snapshot=it.produto_imagem_snapshot,
                )
                for it in pedido.itens
            ],
        )

    # --------- Fluxo 2: confirmar pagamento (mock de API) ----------
    async def confirmar_pagamento(
        self,
        *,
        pedido_id: int,
        metodo: PagamentoMetodoEnum = PagamentoMetodoEnum.PIX,
        gateway: PagamentoGatewayEnum = PagamentoGatewayEnum.PIX_INTERNO,
    ):
        pedido = self.repo.get_pedido(pedido_id)
        if not pedido:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido não encontrado")
        if pedido.valor_total is None or pedido.valor_total <= 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Valor total inválido para pagamento")
        if pedido.transacao and pedido.transacao.status in ("PAGO", "AUTORIZADO"):
            # idempotência simples
            return {"ok": True, "pedido_id": pedido.id, "status_pedido": pedido.status, "transacao_id": pedido.transacao.id}

        try:
            tx = self.repo.criar_transacao_pagamento(
                pedido_id=pedido.id,
                gateway=gateway.value,
                metodo=metodo.value,
                valor=_dec(pedido.valor_total),
            )

            # chama gateway (MOCK por padrão)
            result = await self.gateway.charge(
                order_id=pedido.id,
                amount=_dec(pedido.valor_total),
                metodo=metodo,
                gateway=gateway,
                metadata={"empresa_id": pedido.empresa_id},
            )

            if result.status == PagamentoStatusEnum.PAGO:
                self.repo.atualizar_transacao_status(
                    tx,
                    status="PAGO",
                    provider_transaction_id=result.provider_transaction_id,
                    payload_retorno=result.payload,
                    qr_code=result.qr_code,
                    qr_code_base64=result.qr_code_base64,
                    timestamp_field="pago_em",
                )
                # status do pedido -> ACEITO ("A")
                self.repo.atualizar_status_pedido(pedido, PedidoStatusEnum.A.value, motivo="Pagamento confirmado")
            else:
                self.repo.atualizar_transacao_status(
                    tx,
                    status="RECUSADO",
                    provider_transaction_id=result.provider_transaction_id,
                    payload_retorno=result.payload,
                )

            self.repo.commit()
            return {"ok": True, "pedido_id": pedido.id, "status_pedido": pedido.status, "transacao_id": tx.id}

        except Exception as e:
            self.repo.rollback()
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Erro ao confirmar pagamento: {e}")
